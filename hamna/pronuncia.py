"""
Diccionario de pronunciación (Ajustes → Voz): «Escrito» → «Cómo se dice».

Se aplica al texto justo antes de mandarlo al motor de voz (cualquiera), ya con
las variables resueltas; lo escrito en las secciones y anuncios no cambia.

Reglas:
  · solo palabras completas: «FT8» cambia en «(FT8),» pero no dentro de «FT8CALL»;
  · primero los términos más largos («FT8 DX» antes que «FT8»), sin importar el orden;
  · mayúsculas exactas por defecto; cada término puede ignorarlas («Aa»);
  · una sola pasada: lo que se pone en «Cómo se dice» no se vuelve a revisar;
  · los espacios de un término de varias palabras aceptan cualquier espacio.

Se guarda en los ajustes (pron_dict) como [{"e": escrito, "d": dicho, "i": ignorar mayúsculas}].
"""
import re

MAX = 500
MAX_E = 80
MAX_D = 200
_cache = {"clave": None, "rx": None, "mapa": None}


def normalizar(lista):
    """Valida y limpia la lista que manda la página. Lanza ValueError con un mensaje claro."""
    if not isinstance(lista, list):
        raise ValueError("Diccionario inválido")
    out, vistos = [], {}
    for n, x in enumerate(lista, 1):
        if not isinstance(x, dict):
            raise ValueError("Diccionario inválido (renglón {})".format(n))
        e = re.sub(r"\s+", " ", str(x.get("e") or "")).strip()
        d = re.sub(r"\s+", " ", str(x.get("d") or "")).strip()
        i = bool(x.get("i"))
        if not e and not d:
            continue
        if not e or not d:
            raise ValueError("Renglón {}: falta «{}»".format(n, "Escrito" if not e else "Cómo se dice"))
        if len(e) > MAX_E or len(d) > MAX_D:
            raise ValueError("Renglón {}: muy largo (máximo {} y {} letras)".format(n, MAX_E, MAX_D))
        clave = e.lower() if i else e
        # Un término repetido: el último gana (así «Pegar lista» puede corregir uno existente)
        if clave in vistos:
            out[vistos[clave]] = {"e": e, "d": d, "i": i}
            continue
        vistos[clave] = len(out)
        out.append({"e": e, "d": d, "i": i})
    if len(out) > MAX:
        raise ValueError("Máximo {} términos".format(MAX))
    return out


def _compilar(lista):
    clave = repr(lista)
    if _cache["clave"] == clave:
        return _cache["rx"], _cache["mapa"]
    terms = sorted(lista, key=lambda x: -len(x["e"]))
    mapa = {}                                   # minúsculas → [(término, dicho, ignora)]
    partes = []
    for t in terms:
        mapa.setdefault(t["e"].lower(), []).append(t)
        partes.append(r"\s+".join(re.escape(p) for p in t["e"].split(" ")))
    rx = None
    if partes:
        # Sin letras/números pegados a los lados = palabra completa. La búsqueda ignora
        # mayúsculas y cada término decide después si las respeta (Python 3.5 no tiene (?i:…)).
        rx = re.compile(r"(?<!\w)(?:" + "|".join(partes) + r")(?!\w)", re.IGNORECASE | re.UNICODE)
    _cache.update(clave=clave, rx=rx, mapa=mapa)
    return rx, mapa


def aplicar(texto, lista):
    """Devuelve (texto para la voz, [términos aplicados])."""
    if not texto or not lista:
        return texto, []
    try:
        rx, mapa = _compilar(lista)
    except re.error:
        return texto, []
    if not rx:
        return texto, []
    usados = []

    def cambia(m):
        hallado = m.group(0)
        plano = re.sub(r"\s+", " ", hallado)
        for t in mapa.get(plano.lower(), []):
            if t["i"] or t["e"] == plano:
                if t["e"] not in usados:
                    usados.append(t["e"])
                return t["d"]
        return hallado                           # misma palabra con otras mayúsculas y el término las respeta

    return rx.sub(cambia, texto), usados


def para_voz(texto, cfg):
    return aplicar(texto, cfg.get("pron_dict") or [])[0]


def toca(texto, terminos):
    """¿El texto usa alguno de estos términos? (para saber qué secciones volver a generar)."""
    return bool(aplicar(texto, terminos)[1])


def cambiados(antes, despues):
    """Términos agregados, modificados o quitados entre dos versiones del diccionario."""
    a = {(x["e"], x["i"]): x["d"] for x in antes or []}
    b = {(x["e"], x["i"]): x["d"] for x in despues or []}
    out = []
    for k in set(a) | set(b):
        if a.get(k) != b.get(k):
            out.append({"e": k[0], "i": k[1], "d": "·"})
    return out
