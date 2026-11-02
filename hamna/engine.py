"""
HAMNA Web — motor de transmisión y programador.

Ciclo de un evento (igual que HAMNA Desktop):

  Sección 1 → [intervalo, PTT suelto] → Sección 2 → … → fin

Con pausa automática, cada sección se corta en tramos de pause_tx_time
segundos. Cada tramo es un solo archivo, así el transmisor no se suelta:

  [silencio PTT] + [anuncio "continuamos"] + audio + [anuncio de pausa]
                                       alerta ↑ mezclada N s antes del corte

Entre tramos el PTT se suelta durante pause_duration segundos y el
siguiente tramo arranca retroceso_secs antes del corte.
"""
import datetime as dt
import logging
import threading
import time
import uuid
from collections import deque
from pathlib import Path

from . import audio, backends, db, paths, settings, tts

log = logging.getLogger("hamna.engine")

TAIL_MIN = 5.0     # no hacer una pausa si después quedan menos de 5 s


class Stopped(Exception):
    pass


class Engine:
    def __init__(self):
        self._lock = threading.RLock()
        self._thread = None
        self._cmd = None
        self._wake = threading.Event()
        self._fired = set()
        self._prewarmed = set()
        self.events = deque(maxlen=80)
        self._reset_status()

    # ── Estado para la interfaz ──────────────────────────────────────────────
    def _reset_status(self):
        self.st = {
            "on_air": False, "state": "idle", "evento_id": None, "evento": "",
            "origen": "", "secciones": [], "cur_sec": -1, "sec_pos": 0.0,
            "countdown": None, "ptt": False, "segment": None, "error": "",
            "started_at": None,
        }
        self._seg_clock = None   # (t0_monotonic, body_offset, body_start, body_len)

    def note(self, msg, level="info"):
        ts = dt.datetime.now().strftime("%H:%M:%S")
        self.events.appendleft({"t": ts, "msg": msg, "level": level})
        getattr(log, "warning" if level == "warn" else level, log.info)(msg)

    def status(self):
        with self._lock:
            s = dict(self.st)
            s["secciones"] = [dict(x) for x in self.st["secciones"]]
            if self._seg_clock and s["state"] == "tx":
                t0, off, start, blen = self._seg_clock
                into = time.monotonic() - t0 - off
                s["sec_pos"] = start + min(max(into, 0.0), blen)
            if s["countdown"] is not None:
                s["countdown"] = max(0, round(s["countdown"] - time.monotonic()))
            total = sum(x["duracion"] for x in s["secciones"])
            done = sum(x["duracion"] for x in s["secciones"][:max(s["cur_sec"], 0)])
            s["elapsed"] = done + (s["sec_pos"] if s["cur_sec"] >= 0 else 0)
            s["total"] = total
            s["log"] = list(self.events)[:40]
            return s

    def _set(self, **kw):
        with self._lock:
            self.st.update(kw)

    # ── Comandos ─────────────────────────────────────────────────────────────
    def busy(self):
        return bool(self._thread and self._thread.is_alive())

    def start_event(self, evento_id, origen = "manual"):
        ev = db.get_evento(evento_id)
        if not ev:
            raise ValueError("El evento no existe")
        if not db.get_secciones_by_evento(evento_id):
            raise ValueError("El evento no tiene secciones")
        self.stop(wait=True)
        self._start(lambda: self._run_event(ev, origen))

    def play_single(self, path, label):
        """Transmite un solo audio (prueba)."""
        self.stop(wait=True)
        self._start(lambda: self._run_single(path, label))

    def _start(self, target):
        self._cmd = None
        with self._lock:
            # Marcar "preparando" ya, para que la página no vea un instante "fuera del aire"
            self.st.update(error="", on_air=True, state="preparing")
        self._wake.clear()
        self._thread = threading.Thread(target=self._guard(target), daemon=True)
        self._thread.start()

    def _guard(self, fn):
        def run():
            try:
                fn()
            except Stopped:
                self.note("Transmisión detenida por el operador", "warn")
            except Exception as e:
                log.exception("Fallo en la transmisión")
                self.note("Error: {}".format(e), "error")
                self._set(error=str(e))
            finally:
                err = self.st.get("error", "")
                with self._lock:
                    self._reset_status()
                    self.st["error"] = err
        return run

    def command(self, cmd):
        if cmd not in ("stop", "next", "skip_pause", "pause", "resume"):
            raise ValueError(cmd)
        if not self.busy():
            return
        self._cmd = cmd
        self._wake.set()

    def stop(self, wait=False):
        if self.busy():
            self.command("stop")
            if wait and self._thread:
                self._thread.join(timeout=8)

    # ── Esperas interrumpibles ───────────────────────────────────────────────
    def _take(self, *accept):
        """Consume el comando pendiente. 'stop' siempre interrumpe; los que
        no aplican en este momento se descartan."""
        c = self._cmd
        if c == "stop":
            raise Stopped()
        if not c:
            return None
        self._cmd = None
        return c if (not accept or c in accept) else None

    def _wait(self, seconds, *accept):
        end = time.monotonic() + max(0.0, seconds)
        with self._lock:
            self.st["countdown"] = end
        try:
            while True:
                c = self._take(*accept)
                if c:
                    return c
                left = end - time.monotonic()
                if left <= 0:
                    return None
                self._wake.wait(min(left, 0.5))
                self._wake.clear()
        finally:
            with self._lock:
                self.st["countdown"] = None

    # ── Preparación de audio ─────────────────────────────────────────────────
    def _target(self, cfg):
        return float(cfg.get("normalize_target", -18)) if cfg.get("section_normalize") else None

    def _pause_target(self, cfg):
        t = self._target(cfg)
        if t is None:
            return None
        return t + (int(cfg.get("pause_volume", 95)) - 100) * 0.4

    def _pause_files(self, cfg):
        out = {}
        for key in ("pause_alert_file", "pause_announcement_file", "pause_resume_file"):
            name = cfg.get(key) or ""
            p = paths.sonidos_dir() / name if name else None
            if p and p.is_file():
                out[key] = audio.prepare(p, self._pause_target(cfg))
        return out

    def _regen(self, sec, ev, secs, cfg):
        ctx = tts.event_context(ev, secs)
        ctx.update(titulo=sec.get("titulo") or sec.get("nombre"),
                   descripcion=sec.get("descripcion") or "")
        out = paths.tmp_dir() / "regen_{}_{}".format(sec['id'], uuid.uuid4().hex[:6])
        try:
            src = tts.synthesize(sec["texto_tts"], cfg, out, ctx)
            sec["_prep"] = audio.prepare(src, self._target(cfg))
            sec["duracion"] = audio.duration(sec["_prep"])
            self.note("TTS regenerado: {}".format(sec['nombre']))
        except Exception as e:
            self.note("No se pudo regenerar '{}': {} — uso la versión guardada".format(sec['nombre'], e), "warn")

    def prepare_event(self, evento_id):
        """Deja en caché los audios de un evento (se llama 20 min antes)."""
        cfg = settings.load()
        n = 0
        for s in db.get_secciones_by_evento(evento_id):
            p = self._file_of(s)
            if p:
                audio.prepare(p, self._target(cfg))
                n += 1
        self._pause_files(cfg)
        return n

    @staticmethod
    def _file_of(sec):
        name = sec.get("ruta_archivo") or ""
        if not name:
            return None
        p = Path(name)
        if not p.is_absolute():
            p = paths.audios_dir() / name
        return p if p.is_file() else None

    # ── Transmisión ──────────────────────────────────────────────────────────
    def _run_single(self, path, label):
        cfg = settings.load()
        be = backends.make(cfg)
        prep = audio.prepare(path, self._target(cfg))
        out = paths.tmp_dir() / "seg_{}.wav".format(uuid.uuid4().hex[:8])
        info = audio.build_segment(prep, 0, audio.duration(prep), out,
                                   lead=float(cfg.get("ptt_on_delay", 0)))
        self._set(on_air=True, state="tx", evento=label, origen="prueba",
                  secciones=[{"nombre": label, "duracion": info["body_len"], "tipo": "Prueba"}],
                  cur_sec=0, started_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.note("Prueba al aire: {}".format(label))
        self._play(be, out, info, 0.0)
        paths.rm(out)

    def _run_event(self, ev, origen):
        cfg = settings.load()
        be = backends.make(cfg)
        secs = [dict(s) for s in db.get_secciones_by_evento(ev["id"])]
        hid = db.historial_inicio(ev["id"], ev["nombre"], origen)
        result = "incompleto"
        self._set(on_air=True, state="preparing", evento_id=ev["id"], evento=ev["nombre"],
                  origen=origen, error="", cur_sec=-1,
                  started_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  secciones=[{"id": s["id"], "nombre": s["nombre"], "tipo": s["tipo"],
                              "duracion": float(s["duracion"] or 0)} for s in secs])
        self.note("Iniciando «{}» ({}) por {}".format(ev['nombre'], origen, be.name))
        try:
            # Todo se prepara antes de activar el PTT, para no dejar silencio al aire
            for s in secs:
                p = self._file_of(s)
                if p:
                    s["_prep"] = audio.prepare(p, self._target(cfg))
                    s["duracion"] = audio.duration(s["_prep"])
                self._take()
            pf = self._pause_files(cfg)
            self._sync_secs(secs)

            for i, sec in enumerate(secs):
                if i > 0:
                    self._set(state="gap", cur_sec=i, sec_pos=0.0, ptt=False)
                    t0 = time.monotonic()
                    if sec.get("regenerar_antes") and sec.get("texto_tts"):
                        self._regen(sec, ev, secs, cfg)
                        self._sync_secs(secs)
                    gap = float(cfg.get("section_gap", 3))
                    self._wait(gap - (time.monotonic() - t0), "skip_pause")
                elif sec.get("regenerar_antes") and sec.get("texto_tts"):
                    self._regen(sec, ev, secs, cfg)
                    self._sync_secs(secs)
                self._take("next", "skip_pause")
                if not sec.get("_prep"):
                    self.note("«{}» no tiene audio; se omite".format(sec['nombre']), "warn")
                    continue
                self._set(cur_sec=i, sec_pos=0.0)
                self.note("Sección {}/{}: {}".format(i + 1, len(secs), sec['nombre']))
                self._play_section(be, sec, cfg, pf)
            result = "completo"
            self.note("«{}» terminó".format(ev['nombre']))
        except Stopped:
            result = "detenido"
            raise
        except Exception as e:
            result = "error: {}".format(e)
            raise
        finally:
            db.historial_fin(hid, result)
            for s in secs:
                p = s.get("_prep")
                if p and Path(p).parent == paths.tmp_dir():
                    paths.rm(p)

    def _sync_secs(self, secs):
        with self._lock:
            for i, s in enumerate(secs):
                if i < len(self.st["secciones"]):
                    self.st["secciones"][i]["duracion"] = float(s.get("duracion") or 0)

    def _play_section(self, be, sec, cfg, pf):
        body = Path(sec["_prep"])
        dur = audio.duration(body)
        lead = float(cfg.get("ptt_on_delay", 0) or 0)
        pause_on = bool(cfg.get("pause_enabled")) and float(cfg.get("pause_tx_time", 0)) > 10
        tx_time = float(cfg.get("pause_tx_time", 160))
        alert_before = float(cfg.get("pause_alert_before", 0) or 0)
        rewind = float(cfg.get("retroceso_secs", 5)) if cfg.get("retroceso_enabled") else 0.0
        pos, resumed = 0.0, False

        while pos < dur - 0.05:
            end = dur
            if pause_on and dur - pos > tx_time + TAIL_MIN:
                end = pos + tx_time
            last = end >= dur - 0.05
            out = paths.tmp_dir() / "seg_{}.wav".format(uuid.uuid4().hex[:8])
            info = audio.build_segment(
                body, pos, end, out, lead=lead,
                pre=[pf["pause_resume_file"]] if resumed and "pause_resume_file" in pf else [],
                post=[pf["pause_announcement_file"]] if not last and "pause_announcement_file" in pf else [],
                alert=pf.get("pause_alert_file") if not last else None,
                alert_before=alert_before)
            try:
                res = self._play(be, out, info, pos)
            finally:
                paths.rm(out)

            if res == "next":
                return
            if res == "pause":
                # Pausa manual: recordar dónde íbamos y esperar a que reanuden
                cur = self.status()["sec_pos"]
                self._set(state="manual_pause", ptt=False)
                self.note("Pausa manual")
                c = None
                while c is None:
                    c = self._wait(3600, "resume", "next")
                if c == "next":
                    return
                pos = max(0.0, cur - rewind)
                resumed = False
                self.note("Reanudando")
                continue
            if last:
                return
            # Pausa automática
            self._set(state="paused", ptt=False, sec_pos=end)
            self.note("Pausa automática de {} s".format(int(float(cfg.get('pause_duration', 10)))))
            c = self._wait(float(cfg.get("pause_duration", 10)), "skip_pause", "next")
            if c == "next":
                return
            pos = max(0.0, end - rewind)
            resumed = True

    def _play(self, be, wav, info, body_start):
        """Transmite un tramo. Devuelve 'done', 'next' o 'pause'."""
        with self._lock:
            self.st.update(state="tx", ptt=True, sec_pos=body_start)
            self._seg_clock = (time.monotonic(), info["body_offset"], body_start, info["body_len"])
        got = {}

        def abort():
            c = self._cmd
            if c in ("stop", "next", "pause"):
                got["c"] = c
                return True
            return False

        try:
            ok = be.play(wav, info["total"], abort)
        finally:
            with self._lock:
                self._seg_clock = None
                self.st["ptt"] = False
        if ok:
            return "done"
        return self._take("next", "pause") or "done"

    # ── Programador ──────────────────────────────────────────────────────────
    @staticmethod
    def applies_today(row, day):
        rec = (row.get("recurrencia") or "ninguna").lower()
        fecha = row.get("fecha") or ""
        try:
            orig = dt.datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            orig = None
        if rec == "ninguna":
            return orig == day
        if orig and day < orig:
            return False
        if rec == "diaria":
            return True
        if rec == "semanal":
            return orig is not None and day.weekday() == orig.weekday()
        if rec == "lun-vie":
            return day.weekday() < 5
        return False

    @classmethod
    def next_run(cls, row, now = None):
        now = now or dt.datetime.now()
        try:
            h, m = map(int, (row.get("hora") or "")[:5].split(":"))
        except ValueError:
            return None
        for d in range(0, 8 if row.get("recurrencia") != "ninguna" else 400):
            day = now.date() + dt.timedelta(days=d)
            when = dt.datetime.combine(day, dt.time(h, m))
            if when >= now.replace(second=0, microsecond=0) and cls.applies_today(row, day):
                return when
        return None

    def scheduler_loop(self):
        log.info("Programador iniciado")
        last_cleanup = 0.0
        while True:
            try:
                self._tick()
                if time.time() - last_cleanup > 3600:
                    audio.cleanup()
                    last_cleanup = time.time()
            except Exception:
                log.exception("Error en el programador")
            time.sleep(5)

    def _tick(self):
        now = dt.datetime.now()
        today = now.date()
        hhmm = now.strftime("%H:%M")
        for row in db.get_programacion(solo_activos=True):
            if not self.applies_today(row, today):
                continue
            try:
                h, m = map(int, row["hora"][:5].split(":"))
            except ValueError:
                continue
            mins_left = (h * 60 + m) - (now.hour * 60 + now.minute)
            if 0 < mins_left <= 20:
                key = (row["id"], today)
                if key not in self._prewarmed:
                    self._prewarmed.add(key)
                    threading.Thread(target=self._prewarm, args=(row,), daemon=True).start()
            if row["hora"][:5] != hhmm:
                continue
            key = (row["id"], today, hhmm)
            if key in self._fired:
                continue
            self._fired.add(key)
            if self.busy() and self.st.get("evento_id") == row["evento_id"]:
                continue
            self.note("Programador: inicia «{}» a las {}".format(row['evento_nombre'], hhmm))
            try:
                self.start_event(row["evento_id"], origen="programado")
            except Exception as e:
                self.note("Programador: no se pudo iniciar «{}»: {}".format(row['evento_nombre'], e), "error")
        # olvidar disparos de otros días
        self._fired = {k for k in self._fired if k[1] == today}
        self._prewarmed = {k for k in self._prewarmed if k[1] == today}

    def _prewarm(self, row):
        try:
            n = self.prepare_event(row["evento_id"])
            self.note("Audios de «{}» preparados ({})".format(row['evento_nombre'], n))
        except Exception as e:
            self.note("Preparación anticipada falló: {}".format(e), "warn")


engine = Engine()
