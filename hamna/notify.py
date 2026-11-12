"""
HAMNA Web — avisos por Telegram.

Se configuran en Ajustes → Avisos: el token de un bot (se crea con @BotFather)
y el chat donde llegan los mensajes. Los envíos van en segundo plano (nunca
detienen una transmisión) y un mismo aviso no se repite en 15 minutos.
"""
import datetime as dt
import html
import json
import re
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import settings

log = logging.getLogger("hamna.avisos")

API = "https://api.telegram.org/bot{}/{}"
DEDUPE_SECS = 15 * 60
_recent = {}
_lock = threading.Lock()

# Qué se avisa (claves de settings) y su valor por defecto
KINDS = {
    "error": "tg_on_error",          # evento que no inició o terminó con error
    "previa": "tg_on_preflight",     # revisión 30 min antes con problemas
    "sync": "tg_on_sync",            # sincronización automática fallida
    "inicio": "tg_on_start",         # resumen al empezar cada transmisión
    "fin": "tg_on_end",              # resumen al terminar cada transmisión
    "proximo": "tg_on_upcoming",     # N minutos antes de un evento programado
    "seccion": "tg_on_section",      # al empezar cada sección
}
MAX_LINES = 40          # Telegram corta en 4096 caracteres



def esc(s):
    return html.escape(str(s if s is not None else ""), quote=False)


def header(cfg=None):
    cfg = cfg or settings.load()
    est = cfg.get("station_name") or "HAMNA Web"
    nodo = cfg.get("node") or ""
    return "📻 <b>{}</b>{}".format(esc(est), " · nodo {}".format(esc(nodo)) if nodo else "")


def _call(token, method, params, timeout=15):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API.format(token, method), data=data,
                                 headers={"User-Agent": "HAMNA-Web"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            out = json.loads(e.read().decode("utf-8"))
        except Exception:
            out = {"ok": False, "description": "HTTP {}".format(e.code)}
    except Exception as e:
        raise RuntimeError("No pude conectar con Telegram: {}".format(e))
    if not out.get("ok"):
        raise RuntimeError("Telegram respondió: {}".format(out.get("description") or "error"))
    return out.get("result")


def send_now(text, token=None, chat=None):
    """Envía ya (para la prueba). Devuelve nada o lanza RuntimeError."""
    cfg = settings.load()
    token = (token or cfg.get("tg_token") or "").strip()
    chat = (chat or cfg.get("tg_chat") or "").strip()
    if not token or not chat:
        raise ValueError("Falta el token del bot o el chat")
    _call(token, "sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML",
                                 "disable_web_page_preview": "true"})


def send(kind, text, dedupe=None):
    """Aviso en segundo plano si está activado ese tipo. No lanza errores."""
    cfg = settings.load()
    if not cfg.get("tg_enabled") or not cfg.get("tg_token") or not cfg.get("tg_chat"):
        return
    key = KINDS.get(kind)
    if key and not cfg.get(key):
        return
    dk = dedupe or (kind + ":" + text)
    now = time.time()
    with _lock:
        if now - _recent.get(dk, 0) < DEDUPE_SECS:
            return
        _recent[dk] = now
        if len(_recent) > 300:
            for k in [k for k, t in _recent.items() if now - t > DEDUPE_SECS]:
                del _recent[k]
    msg = header(cfg) + "\n" + text

    def work():
        for intento in range(3):
            try:
                send_now(msg)
                return
            except Exception as e:
                if intento == 2:
                    log.warning("No se pudo enviar el aviso de Telegram: %s", e)
                time.sleep(5 * (intento + 1))
    threading.Thread(target=work, daemon=True).start()


def find_chats(token=None):
    """Chats que le escribieron al bot recientemente (para no buscar el ID a mano)."""
    token = (token or settings.get("tg_token") or "").strip()
    if not token:
        raise ValueError("Falta el token del bot")
    me = _call(token, "getMe", {})
    upd = _call(token, "getUpdates", {"limit": 100, "timeout": 0})
    chats = {}
    for u in upd or []:
        m = u.get("message") or u.get("channel_post") or u.get("my_chat_member") or {}
        c = m.get("chat") or {}
        if "id" in c:
            name = c.get("title") or " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) \
                or c.get("username") or str(c["id"])
            chats[str(c["id"])] = {"id": str(c["id"]), "nombre": name, "tipo": c.get("type", "")}
    return {"bot": "@" + (me or {}).get("username", ""), "chats": list(chats.values())}


# ── Mensajes ─────────────────────────────────────────────────────────────────
def upcoming_minutes(cfg=None):
    """Minutos antes en que se avisa («15» o «60, 15, 5»)."""
    cfg = cfg or settings.load()
    out = set()
    for x in re.split(r"[,;\s]+", str(cfg.get("tg_upcoming_mins") or "")):
        if x.isdigit() and 1 <= int(x) <= 1440:
            out.add(int(x))
    return sorted(out, reverse=True)


def dur(s):
    s = int(round(float(s or 0)))
    h, m, x = s // 3600, (s % 3600) // 60, s % 60
    return "{}:{:02d}:{:02d}".format(h, m, x) if h else "{}:{:02d}".format(m, x)


def _title(ev):
    t = "<b>{}</b>".format(esc(ev.get("nombre")))
    if ev.get("numero"):
        t += " #{}".format(esc(ev["numero"]))
    return t


def _short(name, n=60):
    name = str(name or "")
    return name if len(name) <= n else name[:n - 1] + "…"


def _has_audio(s):
    return bool(s.get("tiene_audio", s.get("ruta_archivo")))


MARKS = {"ok": "✓", "parcial": "◐", "sin_audio": "✗", None: "·"}
NOTES = {"parcial": " — interrumpida", "sin_audio": " — sin audio", None: " — no se transmitió"}


def _sec_lines(secs, estados=None):
    lines = []
    for i, s in enumerate(secs):
        if i == MAX_LINES:
            lines.append("… y {} más".format(len(secs) - MAX_LINES))
            break
        name = esc(_short(s.get("nombre")))
        if estados is None:
            extra = " · " + dur(s.get("duracion")) if _has_audio(s) else " · ⚠ sin audio"
            lines.append("{}. {}{}".format(i + 1, name, extra))
        else:
            e = estados[i]
            lines.append("{} {}. {}{}".format(MARKS.get(e, "·"), i + 1, name,
                                              " · " + dur(s.get("duracion")) if e == "ok" else NOTES.get(e, "")))
    return lines


def _approx(secs, gap):
    con = [s for s in secs if _has_audio(s)]
    return sum(float(s.get("duracion") or 0) for s in con) + max(0, len(con) - 1) * float(gap or 0)


def _links(conexiones):
    out = []
    for a in conexiones or []:
        try:
            from . import links
            txt = links.describe(links.validate(a))
        except Exception:
            txt = "{} {}".format(a.get("accion", ""), a.get("destino", "")).strip()
        m = float(a.get("minutos") or 0)
        cuando = ("{:g} min antes".format(m) if m else "al iniciar") if a.get("momento") == "antes" \
            else ("{:g} min después".format(m) if m else "al terminar")
        out.append("• {} ({})".format(esc(txt), cuando))
    return out


def msg_upcoming(ev, secs, when, mins, conexiones=None, gap=3):
    sin = sum(1 for s in secs if not _has_audio(s))
    t = ["⏰ {} sale en <b>{} min</b> ({})".format(_title(ev), mins, when.strftime("%H:%M")),
         "📋 {} secciones · aprox. {}{}".format(len(secs), dur(_approx(secs, gap)),
                                                 " · ⚠ {} sin audio".format(sin) if sin else "")]
    ln = _links(conexiones)
    if ln:
        t += ["🔗 Conexiones:"] + ln
    return "\n".join(t)


def msg_start(ev, secs, origen, inicio, gap=3, nodo="", conexiones=None):
    total = _approx(secs, gap)
    fin = inicio + dt.timedelta(seconds=total)
    t = ["▶ Inicia {}".format(_title(ev))]
    det = [x for x in (esc(ev.get("tipo") or ""), "origen: " + esc(origen), esc(nodo)) if x]
    t.append(" · ".join(det))
    t.append("🕗 {} · duración aprox. {} · termina ~{}".format(
        inicio.strftime("%H:%M:%S"), dur(total), fin.strftime("%H:%M")))
    t += ["", "<b>Secciones ({})</b>".format(len(secs))] + _sec_lines(secs)
    ln = _links(conexiones)
    if ln:
        t += ["", "🔗 Conexiones:"] + ln
    return "\n".join(t)


def msg_section(ev, secs, i, inicio=None):
    s = secs[i]
    t = ["🔹 {} · sección {}/{}".format(_title(ev), i + 1, len(secs)),
         "<b>{}</b> · {}".format(esc(_short(s.get("nombre"), 80)), dur(s.get("duracion")))]
    nxt = next((j for j in range(i + 1, len(secs)) if _has_audio(secs[j])), None)
    t.append("Sigue: {}. {}".format(nxt + 1, esc(_short(secs[nxt].get("nombre")))) if nxt is not None
             else "Es la última sección")
    if inicio:
        t.append("⏱ {} desde el inicio".format(dur((dt.datetime.now() - inicio).total_seconds())))
    return "\n".join(t)


def msg_end(ev, secs, estados, inicio, fin, result):
    if result == "completo":
        head = "✅ {} terminó".format(_title(ev))
    elif result == "detenido":
        head = "⏹ {} fue detenido".format(_title(ev))
    else:
        head = "❌ {} terminó con error\n{}".format(_title(ev), esc(result))
    ok_n = sum(1 for e in estados if e == "ok")
    t = [head, "🕗 {} → {} · duró {}".format(inicio.strftime("%H:%M:%S"), fin.strftime("%H:%M:%S"),
                                             dur((fin - inicio).total_seconds())),
         "📋 Transmitidas {} de {}".format(ok_n, len(secs)), ""] + _sec_lines(secs, estados)
    return "\n".join(t)
