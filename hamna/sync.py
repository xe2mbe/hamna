"""
HAMNA Web — sincronizar un evento desde otro nodo (lado del que recibe).

Ejemplo: el nodo de Tijuana sincroniza su evento «Retransmisión» desde el
«Boletín Dominical» del hub. Trae la lista de secciones, descarga solo los
audios que cambiaron (se comparan por sha256), respeta las secciones
marcadas como locales (Entrada/Salida propias) y deja todo preparado.

Seguridad: el código de acceso es de solo lectura y vale para un evento.
Si el origen usa HTTPS con certificado propio, la primera vez se guarda su
huella y en cada conexión se comprueba (nadie puede hacerse pasar por él).
"""
import datetime as dt
import hashlib
import http.client
import json
import logging
import re
import shutil
import ssl
import threading
import time
import uuid
from urllib.parse import urlparse

from . import audio, db, paths

log = logging.getLogger("hamna.sync")

_running = set()
_run_lock = threading.Lock()
_fired = set()


def init():
    with db.conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS sincronizaciones (
                evento_id    INTEGER PRIMARY KEY REFERENCES eventos(id) ON DELETE CASCADE,
                url          TEXT NOT NULL,
                token        TEXT NOT NULL,
                cert_sha256  TEXT DEFAULT '',
                remoto       TEXT DEFAULT '',
                dias         TEXT DEFAULT '',
                hora         TEXT DEFAULT '',
                antes_horas  REAL DEFAULT 0,
                activo       INTEGER DEFAULT 1,
                ultimo       REAL,
                resultado    TEXT DEFAULT '',
                ok           INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS sync_map (
                evento_id  INTEGER NOT NULL,
                remoto_uid TEXT NOT NULL,
                seccion_id INTEGER NOT NULL REFERENCES secciones(id) ON DELETE CASCADE,
                sha256     TEXT DEFAULT '',
                local      INTEGER DEFAULT 0,
                PRIMARY KEY (evento_id, remoto_uid));
        """)


# ── HTTP con huella del certificado ──────────────────────────────────────────
def _norm_url(url):
    url = (url or "").strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    u = urlparse(url)
    if not u.hostname:
        raise ValueError("Dirección inválida")
    base = u.path if u.path.endswith("/") else u.path + "/"
    return u.scheme, u.hostname, u.port, base


def _open(url, token, path, pin=""):
    """Devuelve (respuesta, huella_del_certificado, conexión)."""
    scheme, host, port, base = _norm_url(url)
    if scheme == "https":
        ctx = ssl.SSLContext(getattr(ssl, "PROTOCOL_TLS_CLIENT", ssl.PROTOCOL_SSLv23))
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE            # certificados propios: se fija la huella
        conn = http.client.HTTPSConnection(host, port or 443, timeout=30, context=ctx)
        conn.connect()
        fp = hashlib.sha256(conn.sock.getpeercert(True)).hexdigest()
        if pin and fp != pin:
            conn.close()
            raise RuntimeError("El certificado del nodo de origen cambió. Si lo renovaron, "
                               "vuelve a probar la conexión y guarda la configuración.")
    else:
        conn = http.client.HTTPConnection(host, port or 80, timeout=30)
        fp = ""
    conn.request("GET", base + path, headers={"X-HAMNA-Share": token, "User-Agent": "HAMNA-Web-sync"})
    r = conn.getresponse()
    if r.status == 401:
        conn.close()
        raise RuntimeError("El nodo de origen rechazó el código de acceso")
    if r.status != 200:
        conn.close()
        raise RuntimeError("El nodo de origen respondió {} {}".format(r.status, r.reason))
    return r, fp, conn


def _json(url, token, path, pin=""):
    r, fp, conn = _open(url, token, path, pin)
    try:
        return json.loads(r.read().decode("utf-8")), fp
    finally:
        conn.close()


def probe(url, token):
    data, fp = _json(url, token, "api/remoto/evento")
    secs = data.get("secciones") or []
    return {"evento": data.get("evento", {}).get("nombre"), "numero": data.get("evento", {}).get("numero"),
            "secciones": len(secs), "audios_mb": round(sum((s.get("archivo") or {}).get("tam", 0)
                                                            for s in secs) / 1e6, 1),
            "huella": fp}


def _download(cfg, rsec, dest_dir, prefix):
    a = rsec["archivo"]
    tmp = paths.tmp_dir() / ("sync_" + uuid.uuid4().hex)
    r, _, conn = _open(cfg["url"], cfg["token"], "api/remoto/audio/{}".format(rsec["id"]), cfg["cert_sha256"])
    h = hashlib.sha256()
    try:
        with open(str(tmp), "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
    finally:
        conn.close()
    if h.hexdigest() != a["sha256"]:
        paths.rm(tmp)
        raise RuntimeError("El audio de «{}» llegó incompleto".format(rsec["nombre"]))
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", rsec["nombre"]).strip("_")[:50] or "audio"
    dest = dest_dir / "{}_{}{}".format(prefix, safe, a.get("ext") or ".mp3")
    shutil.move(str(tmp), str(dest))
    return dest


# ── Configuración ────────────────────────────────────────────────────────────
def get_config(eid):
    return db.row("SELECT * FROM sincronizaciones WHERE evento_id=?", (eid,))


def save_config(eid, url, token, cert, remoto, dias, hora, antes_horas, activo):
    _norm_url(url)
    if hora and not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", hora):
        raise ValueError("Hora inválida (HH:MM)")
    dias = ",".join(str(d) for d in sorted({int(d) for d in dias if str(d).isdigit() and 0 <= int(d) <= 6}))
    old = get_config(eid)
    token = token or (old["token"] if old else "")
    if not token:
        raise ValueError("Falta el código de acceso")
    with db.conn() as c:
        c.execute("""INSERT OR REPLACE INTO sincronizaciones
            (evento_id, url, token, cert_sha256, remoto, dias, hora, antes_horas, activo, ultimo, resultado, ok)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (eid, url.strip(), token, cert or (old["cert_sha256"] if old else ""), remoto or "",
                   dias, hora or "", float(antes_horas or 0), 1 if activo else 0,
                   old["ultimo"] if old else None, old["resultado"] if old else "", old["ok"] if old else 0))


def delete_config(eid):
    db.execute("DELETE FROM sincronizaciones WHERE evento_id=?", (eid,))
    db.execute("DELETE FROM sync_map WHERE evento_id=?", (eid,))


def mapping(eid):
    return {r["seccion_id"]: r for r in db.rows("SELECT * FROM sync_map WHERE evento_id=?", (eid,))}


def set_local(eid, sid, local):
    db.execute("UPDATE sync_map SET local=? WHERE evento_id=? AND seccion_id=?", (1 if local else 0, eid, sid))


def busy(eid):
    with _run_lock:
        return eid in _running


# ── Sincronizar ──────────────────────────────────────────────────────────────
def run(eid, origen="manual"):
    with _run_lock:
        if eid in _running:
            raise RuntimeError("Ya se está sincronizando")
        _running.add(eid)
    try:
        return _run(eid, origen)
    except Exception as e:
        msg = str(e)
        db.execute("UPDATE sincronizaciones SET ultimo=?, resultado=?, ok=0 WHERE evento_id=?",
                   (time.time(), msg[:300], eid))
        log.warning("Sincronización del evento #%s (%s) falló: %s", eid, origen, msg)
        if not str(origen).startswith("manual"):
            from . import notify
            ev = db.get_evento(eid) or {}
            notify.send("sync", "❌ Falló la sincronización de <b>{}</b>\n{}".format(
                notify.esc(ev.get("nombre", "#{}".format(eid))), notify.esc(msg)), dedupe="sync:{}".format(eid))
        raise
    finally:
        with _run_lock:
            _running.discard(eid)


def _run(eid, origen):
    cfg = get_config(eid)
    if not cfg:
        raise ValueError("Este evento no tiene sincronización configurada")
    t0 = time.time()
    data, fp = _json(cfg["url"], cfg["token"], "api/remoto/evento", cfg["cert_sha256"])
    if fp and not cfg["cert_sha256"]:
        db.execute("UPDATE sincronizaciones SET cert_sha256=? WHERE evento_id=?", (fp, eid))
        cfg = dict(cfg, cert_sha256=fp)
    remote = data.get("secciones") or []
    rows = {r["remoto_uid"]: r for r in db.rows("SELECT * FROM sync_map WHERE evento_id=?", (eid,))}
    before = [s["id"] for s in db.get_secciones_by_evento(eid)]
    mapped_sids = {r["seccion_id"] for r in rows.values()}
    nuevos = cambiados = 0
    bajado = 0
    order, cont = [], {}
    for rs in remote:
        m = rows.get(rs["uid"])
        sid = m["seccion_id"] if m and db.get_seccion(m["seccion_id"]) else None
        if sid and m["local"]:
            order.append(sid)                        # sección propia de este nodo: no se toca
            continue
        if not sid:
            sid = db.insert_seccion(rs["nombre"], rs.get("tipo") or "Audio", rs.get("texto_tts"),
                                    rs.get("regenerar_antes"), rs.get("titulo"), rs.get("descripcion"))
            # Las de texto a voz (Entrada/Salida) se copian una vez y quedan como locales
            local = 1 if (rs.get("tipo") == "TTS") else 0
            db.execute("INSERT OR REPLACE INTO sync_map (evento_id, remoto_uid, seccion_id, sha256, local)"
                       " VALUES (?,?,?,?,?)", (eid, rs["uid"], sid, "", local))
            m = {"sha256": "", "local": local}
            nuevos += 1
        else:
            db.update_seccion(sid, nombre=rs["nombre"], titulo=rs.get("titulo"), descripcion=rs.get("descripcion"),
                              texto_tts=rs.get("texto_tts"), regenerar_antes=rs.get("regenerar_antes"))
        a = rs.get("archivo")
        if a and a.get("sha256") != (m.get("sha256") or ""):
            old = db.get_seccion(sid)
            dest = _download(cfg, rs, paths.audios_dir(), sid)
            if old and old.get("ruta_archivo") and old["ruta_archivo"] != dest.name:
                paths.rm(paths.audios_dir() / old["ruta_archivo"])
            db.update_seccion(sid, ruta_archivo=dest.name, duracion=audio.duration(dest))
            db.execute("UPDATE sync_map SET sha256=? WHERE evento_id=? AND seccion_id=?", (a["sha256"], eid, sid))
            cambiados += 1
            bajado += a.get("tam", 0)
        order.append(sid)
        cont[sid] = rs.get("contabilizable", True)
    # Secciones que ya no están en el origen: fuera del evento (y se borran si solo eran de aquí)
    remote_uids = {rs["uid"] for rs in remote}
    quitadas = 0
    for uid, m in rows.items():
        if uid in remote_uids or m["local"]:
            continue
        sid = m["seccion_id"]
        db.remove_seccion_from_evento(eid, sid)
        db.execute("DELETE FROM sync_map WHERE evento_id=? AND remoto_uid=?", (eid, uid))
        if not db.row("SELECT 1 FROM evento_secciones WHERE seccion_id=?", (sid,)):
            s = db.get_seccion(sid)
            if s and s.get("ruta_archivo"):
                paths.rm(paths.audios_dir() / s["ruta_archivo"])
            db.delete_seccion(sid)
        quitadas += 1
    # Secciones agregadas a mano en este nodo: conservan su lugar
    for i, sid in enumerate(before):
        if sid not in mapped_sids and sid not in order and db.get_seccion(sid):
            order.insert(min(i, len(order)), sid)
    for sid in order:
        db.add_seccion_to_evento(eid, sid)
    db.set_orden_evento(eid, order)
    for sid, v in cont.items():
        db.set_contabilizable(eid, sid, v)
    num = (data.get("evento") or {}).get("numero")
    ev = db.get_evento(eid)
    if ev and num is not None and num != ev.get("numero"):
        db.update_evento(eid, ev["nombre"], ev.get("tipo_evento_id"), num)
    res = "{} secciones · {} audio{} nuevo{} ({:.1f} MB){}{} · {:.0f} s".format(
        len(order), cambiados, "" if cambiados == 1 else "s", "" if cambiados == 1 else "s", bajado / 1e6,
        " · {} {}".format(nuevos, "sección nueva" if nuevos == 1 else "secciones nuevas") if nuevos else "",
        " · {} quitada{}".format(quitadas, "" if quitadas == 1 else "s") if quitadas else "", time.time() - t0)
    db.execute("UPDATE sincronizaciones SET ultimo=?, resultado=?, ok=1, remoto=? WHERE evento_id=?",
               (time.time(), res, (data.get("evento") or {}).get("nombre") or "", eid))
    log.info("Sincronización del evento #%s (%s): %s", eid, origen, res)
    # Dejar los audios listos para el aire
    from .engine import engine
    threading.Thread(target=engine.prepare_event, args=(eid,), daemon=True).start()
    return res


def run_bg(eid, origen):
    def work():
        try:
            run(eid, origen)
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()


def tick(now=None):
    """Lo llama el programador cada pocos segundos: días/hora fijos y 'N horas antes'."""
    from .engine import Engine
    now = now or dt.datetime.now()
    hhmm = now.strftime("%H:%M")
    for c in db.rows("SELECT * FROM sincronizaciones WHERE activo=1"):
        eid = c["evento_id"]
        dias = {int(d) for d in (c["dias"] or "").split(",") if d.isdigit()}
        if c["hora"] and c["hora"] == hhmm and now.weekday() in {(d - 1) % 7 for d in dias}:
            key = (eid, now.strftime("%Y-%m-%d"), hhmm)
            if key not in _fired:
                _fired.add(key)
                run_bg(eid, "programada")
        horas = float(c["antes_horas"] or 0)
        if horas > 0:
            for p in db.get_programacion(solo_activos=True):
                if p["evento_id"] != eid:
                    continue
                nxt = Engine.next_run(p, now)
                if nxt and dt.timedelta(0) < nxt - now <= dt.timedelta(hours=horas):
                    key = (eid, "antes", nxt.isoformat())
                    if key not in _fired:
                        _fired.add(key)
                        run_bg(eid, "{} h antes de la retransmisión".format(horas))
    if len(_fired) > 500:
        _fired.clear()
