"""
HAMNA Web — favoritos de ASL (Dashboard y bot).

Se guardan en los ajustes (asl_favoritos) como [{nodo, nombre}]. La primera vez
se importan los de AllScan/Supermon (favorites.ini); después se editan en HAMNA,
porque ese archivo es de www-data y el servicio no lo puede escribir.
Los de IRLP están en irlpctl.py.
"""
import logging
import re

from . import settings

log = logging.getLogger("hamna.favoritos")

NODO_RX = re.compile(r"^\d{3,7}$")       # AllStar o EchoLink (3xxxxxx)
MAX_FAVS = 60


def _de_allscan(node):
    from . import bot
    out = []
    for etiqueta, n in bot._favoritos_allscan(node):
        nombre = etiqueta[:-len(n)].rstrip(" ,·-") if etiqueta.endswith(n) else etiqueta
        out.append({"nodo": n, "nombre": nombre.strip()[:60]})
    return out


def asl(node=""):
    """[{nodo, nombre}] del nodo ASL."""
    favs = settings.get("asl_favoritos")
    if favs is None:
        node = str(node or settings.get("node") or "")
        favs = _de_allscan(node) if NODO_RX.match(node) else []
        if favs:
            settings.save({"asl_favoritos": favs})
            log.info("Importé %d favoritos de AllScan", len(favs))
    return [f for f in (favs or []) if isinstance(f, dict) and NODO_RX.match(str(f.get("nodo", "")))]


def guardar_asl(lista):
    if not isinstance(lista, list):
        raise ValueError("Lista de favoritos inválida")
    out = []
    for f in lista:
        if not isinstance(f, dict):
            raise ValueError("Favorito inválido")
        nodo = str(f.get("nodo") or "").strip()
        nombre = str(f.get("nombre") or "").strip()[:60]
        if not NODO_RX.match(nodo):
            raise ValueError("El favorito «{}» necesita un número de nodo de 3 a 7 dígitos".format(nombre or nodo))
        if nodo in {x["nodo"] for x in out}:
            raise ValueError("El nodo {} está repetido".format(nodo))
        out.append({"nodo": nodo, "nombre": nombre})
    if len(out) > MAX_FAVS:
        raise ValueError("Máximo {} favoritos".format(MAX_FAVS))
    settings.save({"asl_favoritos": out})
    return out
