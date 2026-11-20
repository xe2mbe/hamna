"""
HAMNA Web — control del nodo IRLP desde la página y el bot (lo que hacía IRLPvCON).

  habilitar / deshabilitar   $SCRIPT/enable | disable
  dtmf <código>              $SCRIPT/decode <código>, como si llegara por el radio
  timeout on|off             $LOCAL/timeout: desconexión por inactividad
  aux <1-3> on|off           $BIN/auxNon | auxNoff

Todo pasa por bin/hamna-irlp como repeater, que vuelve a validar cada valor.
Los favoritos se guardan en los ajustes (irlp_favoritos); la primera vez se
importan los de IRLPvCON si existen.
"""
import logging
import os
import re

from . import links, sessions, settings

log = logging.getLogger("hamna.irlp")

VCON_CONF = "/var/www/irlpvutil/irlpvcon_conf"
LOG_FILE = "/home/irlp/log/messages"
MAX_FAVS = 30
DTMF_RX = re.compile(r"^[0-9A-Da-d*#]{1,16}$")
NODO_RX = re.compile(r"^\d{4,6}$")


def _vcon_favoritos():
    """Favoritos de IRLPvCON: línea 2 los nombres y línea 3 los números, separados con ~~."""
    try:
        with open(VCON_CONF, encoding="utf-8", errors="replace") as f:
            lineas = f.read().splitlines()
    except OSError:
        return []
    if len(lineas) < 3:
        return []
    nombres, nodos = lineas[1].split("~~"), lineas[2].split("~~")
    out = []
    for nombre, nodo in zip(nombres, nodos):
        nodo = nodo.strip()
        if NODO_RX.match(nodo) and nodo not in {x["nodo"] for x in out}:
            out.append({"nombre": nombre.strip()[:40], "nodo": nodo})
    return out


def favoritos():
    favs = settings.get("irlp_favoritos")
    if favs is None:                                # primera vez: los de IRLPvCON
        favs = _vcon_favoritos()
        if favs:
            settings.save({"irlp_favoritos": favs})
            log.info("Importé %d favoritos de IRLPvCON", len(favs))
    return [f for f in (favs or []) if isinstance(f, dict) and NODO_RX.match(str(f.get("nodo", "")))]


def guardar_favoritos(lista):
    if not isinstance(lista, list):
        raise ValueError("Lista de favoritos inválida")
    out = []
    for f in lista:
        if not isinstance(f, dict):
            raise ValueError("Favorito inválido")
        nodo = str(f.get("nodo") or "").strip()
        nombre = str(f.get("nombre") or "").strip()[:40]
        if not NODO_RX.match(nodo):
            raise ValueError("El favorito «{}» necesita un nodo o reflector de 4 a 6 dígitos".format(nombre or nodo))
        if nodo in {x["nodo"] for x in out}:
            raise ValueError("El nodo {} está repetido".format(nodo))
        out.append({"nombre": nombre, "nodo": nodo})
    if len(out) > MAX_FAVS:
        raise ValueError("Máximo {} favoritos".format(MAX_FAVS))
    settings.save({"irlp_favoritos": out})
    return out


def accion(accion, valor=""):
    """Ejecuta una acción de control. Devuelve una descripción corta de lo que se hizo."""
    valor = str(valor or "").strip()
    if accion == "habilitar":
        links.irlp_helper("enable")
        return "Nodo habilitado"
    if accion == "deshabilitar":
        links.irlp_helper("disable")
        return "Nodo deshabilitado"
    if accion == "dtmf":
        if not DTMF_RX.match(valor):
            raise ValueError("Código DTMF inválido: usa 0-9, A-D, * o # (hasta 16)")
        links.irlp_helper("dtmf", valor.upper())
        return "Código DTMF {}".format(valor.upper())
    if accion == "timeout":
        if valor not in ("on", "off"):
            raise ValueError("Usa on u off")
        links.irlp_helper("timeout", valor)
        return "Desconexión por inactividad " + ("activada" if valor == "on" else "desactivada")
    if accion == "aux":
        m = re.match(r"^([1-3])(on|off)$", valor)
        if not m:
            raise ValueError("Salida AUX inválida")
        links.irlp_helper("aux", m.group(1), m.group(2))
        return "AUX{} {}".format(m.group(1), "encendida" if m.group(2) == "on" else "apagada")
    raise ValueError("Acción desconocida")


def bitacora(n=100):
    """Las últimas n líneas de la bitácora de IRLP (la más nueva al final)."""
    n = max(10, min(int(n or 100), 500))
    try:
        with open(LOG_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            tam = f.tell()
            f.seek(max(0, tam - n * 200))
            lineas = f.read().decode("utf-8", "replace").splitlines()
    except OSError as e:
        raise RuntimeError("No pude leer {}: {}".format(LOG_FILE, e.strerror))
    if tam > n * 200 and lineas:
        lineas = lineas[1:]                         # la primera puede venir cortada
    return lineas[-n:]


def estado(cfg):
    st = sessions.irlp_status(cfg)
    return {"habilitado": st.get("habilitado"), "timeout": st.get("timeout"), "activo": st.get("activo") or "",
            "favoritos": favoritos(),
            "aux": os.path.isfile("/home/irlp/bin/aux1on")}


# ── IRLPvCON: encenderlo o apagarlo desde Ajustes ───────────────────────────
VCON_DIR = "/var/www/html/irlpvcon"
VCON_HTACCESS = (VCON_DIR + "/.htaccess", "/usr/lib/cgi-bin/irlpvcon/.htaccess")


def vcon_estado():
    """{instalado, encendido}. Apagado = su .htaccess lo puso HAMNA en «Require all denied»."""
    if not os.path.isdir(VCON_DIR):
        return {"instalado": False, "encendido": False}
    apagado = False
    for f in VCON_HTACCESS:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                apagado = apagado or "HAMNA-APAGADO" in fh.read()
        except OSError:
            pass
    return {"instalado": True, "encendido": not apagado}


def vcon(encender):
    if not vcon_estado()["instalado"]:
        raise ValueError("IRLPvCON no está instalado en este nodo")
    links.irlp_helper("vcon", "on" if encender else "off")
    return vcon_estado()
