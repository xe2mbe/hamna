"""
HAMNA Web — favoritos de ASL e IRLP (Dashboard y bot), con categorías.

ASL: ajustes asl_favoritos = [{nodo, nombre, categoria}] y asl_fav_categorias =
[nombres en orden]. La primera vez se importan los de AllScan/Supermon
(favorites.ini); después se editan en HAMNA, porque ese archivo es de www-data
y el servicio no lo puede escribir. IRLP usa las mismas reglas (irlpctl.py,
irlp_favoritos / irlp_fav_categorias).

Cada favorito está en UNA categoría. Los que no traen (los de antes de las
categorías) van a «Generales». Una categoría puede quedar vacía.
"""
import logging
import re

from . import settings

log = logging.getLogger("hamna.favoritos")

NODO_RX = re.compile(r"^\d{3,7}$")       # AllStar o EchoLink (3xxxxxx)
MAX_FAVS = 120
MAX_CATS = 30
GENERAL = "Generales"
CAT_MAX_LEN = 40


def _cat(c):
    return re.sub(r"\s+", " ", str(c or "")).strip()[:CAT_MAX_LEN]


def normalizar(favs, cats):
    """(favoritos con su categoría, categorías en orden). No valida: solo ordena lo guardado."""
    out_c, vistas = [], set()
    for c in cats or []:
        c = _cat(c)
        if c and c.lower() not in vistas:
            vistas.add(c.lower())
            out_c.append(c)
    por_min = {c.lower(): c for c in out_c}
    fs = []
    for f in favs or []:
        d = dict(f)
        c = _cat(f.get("categoria")) or GENERAL
        if c.lower() not in por_min:
            por_min[c.lower()] = c
            out_c.append(c)
        d["categoria"] = por_min[c.lower()]
        fs.append(d)
    return fs, (out_c or [GENERAL])


def validar(lista, categorias, nodo_rx, nombre_max, que):
    """Revisa lo que manda la página. Devuelve (favoritos, categorías)."""
    if not isinstance(lista, list):
        raise ValueError("Lista de favoritos inválida")
    if categorias is not None and not isinstance(categorias, list):
        raise ValueError("Lista de categorías inválida")
    cats, vistas = [], set()
    for c in categorias or []:
        c = _cat(c)
        if not c:
            raise ValueError("Hay una categoría sin nombre")
        if c.lower() in vistas:
            raise ValueError("La categoría «{}» está repetida".format(c))
        vistas.add(c.lower())
        cats.append(c)
    por_min = {c.lower(): c for c in cats}
    out = []
    for f in lista:
        if not isinstance(f, dict):
            raise ValueError("Favorito inválido")
        nodo = str(f.get("nodo") or "").strip()
        nombre = str(f.get("nombre") or "").strip()[:nombre_max]
        if not nodo_rx.match(nodo):
            raise ValueError("El favorito «{}» necesita {}".format(nombre or nodo, que))
        if nodo in {x["nodo"] for x in out}:
            raise ValueError("El nodo {} está repetido".format(nodo))
        c = _cat(f.get("categoria")) or GENERAL
        if c.lower() not in por_min:
            por_min[c.lower()] = c
            cats.append(c)
        out.append({"nodo": nodo, "nombre": nombre, "categoria": por_min[c.lower()]})
    if len(out) > MAX_FAVS:
        raise ValueError("Máximo {} favoritos".format(MAX_FAVS))
    if len(cats) > MAX_CATS:
        raise ValueError("Máximo {} categorías".format(MAX_CATS))
    return out, (cats or [GENERAL])


def agrupar(favs, cats):
    """[(categoría, [favoritos])] en orden, sin las vacías."""
    return [(c, [f for f in favs if f.get("categoria") == c]) for c in cats
            if any(f.get("categoria") == c for f in favs)]


def _de_allscan(node):
    from . import bot
    out = []
    for etiqueta, n in bot._favoritos_allscan(node):
        nombre = etiqueta[:-len(n)].rstrip(" ,·-") if etiqueta.endswith(n) else etiqueta
        out.append({"nodo": n, "nombre": nombre.strip()[:60]})
    return out


def asl_todo(node=""):
    """(favoritos [{nodo, nombre, categoria}], categorías) del nodo ASL."""
    favs = settings.get("asl_favoritos")
    if favs is None:
        node = str(node or settings.get("node") or "")
        favs = _de_allscan(node) if NODO_RX.match(node) else []
        if favs:
            settings.save({"asl_favoritos": favs})
            log.info("Importé %d favoritos de AllScan", len(favs))
    favs = [f for f in (favs or []) if isinstance(f, dict) and NODO_RX.match(str(f.get("nodo", "")))]
    return normalizar(favs, settings.get("asl_fav_categorias"))


def asl(node=""):
    """[{nodo, nombre, categoria}] del nodo ASL, en el orden de las categorías."""
    favs, cats = asl_todo(node)
    return [f for _c, fs in agrupar(favs, cats) for f in fs]


def guardar_asl(lista, categorias=None):
    if categorias is None:                       # página vieja: conservar las categorías que había
        categorias = asl_todo()[1]
    favs, cats = validar(lista, categorias, NODO_RX, 60, "un número de nodo de 3 a 7 dígitos")
    settings.save({"asl_favoritos": favs, "asl_fav_categorias": cats})
    return favs, cats
