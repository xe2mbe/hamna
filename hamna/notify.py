"""
HAMNA Web — avisos por Telegram.

Se configuran en Ajustes → Avisos: el token de un bot (se crea con @BotFather)
y el chat donde llegan los mensajes. Los envíos van en segundo plano (nunca
detienen una transmisión) y un mismo aviso no se repite en 15 minutos.
"""
import html
import json
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
    "inicio": "tg_on_start",         # cada transmisión que empieza
    "fin": "tg_on_end",              # cada transmisión que termina
}


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
