"""
HAMNA Web — biblioteca de voz (v1.54). Desde la v1.56 la biblioteca son las
Secciones: lo que haya aquí se pasa solo a secciones sin evento (a_secciones).

Lo de abajo describe la biblioteca original: audios guardados sin horario.

Cada audio de la biblioteca es texto → voz (con su voz propia, como un
anuncio) o un audio subido/grabado, siempre WAV 8 kHz mono, listo para el aire.
No sale solo: desde la biblioteca se escucha, se descarga, se transmite una vez
(«Transmitir ahora», por la misma cola de los anuncios: espera canal libre) o
se usa para programar un anuncio o como audio de una sección de un evento. Al usarlo se COPIA el audio: corregir o
borrar el de la biblioteca no cambia los anuncios ya hechos.

Si el texto lleva variables ({hora}, {fecha_larga}…), la voz se genera otra vez
al transmitirse, como en los anuncios. Entra en los respaldos (carpeta
biblioteca/ y la tabla).
"""
import datetime as dt
import json
import logging
import os
import shutil
import uuid

from . import anuncios, db, paths, settings

log = logging.getLogger("hamna.biblioteca")

MAX_SEG = 600                              # 10 min: también sirve para secciones (en un anuncio rige su tope)
MAX_TXT_LOTE = 20                          # «Cargar varios .txt» de una vez


def carpeta():
    d = paths.data_dir() / "biblioteca"
    if not d.is_dir():
        os.makedirs(str(d), exist_ok=True)
    return d


def init():
    with db.conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS biblioteca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            notas TEXT NOT NULL DEFAULT '',
            tipo TEXT NOT NULL DEFAULT 'tts',       -- tts | audio
            texto TEXT NOT NULL DEFAULT '',
            voz TEXT NOT NULL DEFAULT '',           -- como en anuncios (JSON); vacío = la de Ajustes
            archivo TEXT NOT NULL DEFAULT '',       -- en biblioteca/, WAV 8 kHz
            archivo_nombre TEXT NOT NULL DEFAULT '',
            duracion REAL NOT NULL DEFAULT 0,
            creado TEXT NOT NULL DEFAULT '',
            creado_por TEXT NOT NULL DEFAULT '',
            modificado TEXT NOT NULL DEFAULT '')""")


def _ahora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def ruta(b):
    return carpeta() / b["archivo"] if b.get("archivo") else None


def lista(q="", orden="fecha"):
    sql = "SELECT * FROM biblioteca"
    args = []
    q = (q or "").strip()
    if q:
        sql += " WHERE nombre LIKE ? OR notas LIKE ? OR texto LIKE ?"
        args = ["%" + q + "%"] * 3
    sql += " ORDER BY nombre COLLATE NOCASE" if orden == "nombre" else " ORDER BY modificado DESC, id DESC"
    return db.rows(sql, args)


def uno(bid):
    r = db.row("SELECT * FROM biblioteca WHERE id=?", (bid,))
    if not r:
        raise ValueError("Ese audio ya no está en la biblioteca")
    return r


def _limpio(d):
    b = {}
    b["nombre"] = str(d.get("nombre") or "").strip()[:80]
    if not b["nombre"]:
        raise ValueError("Ponle un nombre")
    b["notas"] = str(d.get("notas") or "").strip()[:500]
    b["tipo"] = "audio" if d.get("tipo") == "audio" else "tts"
    b["texto"] = str(d.get("texto") or "").strip() if b["tipo"] == "tts" else ""
    tope = anuncios.max_chars()
    if len(b["texto"]) > tope:
        raise ValueError("El texto tiene {} caracteres; el máximo es {} (Ajustes → Voz)".format(len(b["texto"]), tope))
    if b["tipo"] == "tts" and not b["texto"]:
        raise ValueError("Escribe el texto")
    voz = anuncios.voz_limpia(d.get("voz") or {}) if b["tipo"] == "tts" else {}
    b["voz"] = json.dumps(voz, sort_keys=True) if voz else ""
    return b


def _voz(texto, cfg, voz):
    nombre = "bi_{}.wav".format(uuid.uuid4().hex[:10])
    dest = carpeta() / nombre
    c2 = anuncios.cfg_con_voz(cfg, voz)
    try:
        dur = anuncios._sintetizar(texto, c2, dest, respaldo=c2 is cfg)
    except Exception:
        paths.rm(dest)
        raise
    if dur > MAX_SEG + 0.5:
        paths.rm(dest)
        raise ValueError("Con esa voz dura {:.0f} s; el máximo es {} s. Acórtalo o divídelo en dos.".format(dur, MAX_SEG))
    return nombre, dur


def _audio(src):
    nombre = "bi_{}.wav".format(uuid.uuid4().hex[:10])
    dest = carpeta() / nombre
    tmp = paths.tmp_dir() / "bi_up_{}.wav".format(uuid.uuid4().hex[:8])   # sox necesita la extensión
    try:
        shutil.copyfile(str(src), str(tmp))
        dur = anuncios._a_aire(tmp, dest, settings.load())
    except Exception as e:
        paths.rm(dest)
        raise ValueError("No pude leer el audio ({}). Súbelo otra vez desde la página.".format(e))
    finally:
        paths.rm(tmp)
    if dur > MAX_SEG + 0.5 or dur < 0.3:
        paths.rm(dest)
        raise ValueError("El audio está vacío" if dur < 0.3 else "El audio dura {:.0f} s; el máximo es {} s".format(dur, MAX_SEG))
    return nombre, dur


def guardar(datos, archivo_subido=None, nombre_subido="", usuario="", bid=None):
    actual = uno(bid) if bid else {}
    b = _limpio(datos)
    viejo = actual.get("archivo") or ""
    nuevo = None
    if b["tipo"] == "audio":
        if archivo_subido:
            nuevo, b["duracion"] = _audio(archivo_subido)
            b["archivo_nombre"] = (nombre_subido or "audio.wav")[:80]
        elif actual.get("tipo") == "audio" and viejo:
            b["duracion"], b["archivo_nombre"] = actual["duracion"], actual["archivo_nombre"]
        else:
            raise ValueError("Sube o graba el audio")
    else:
        b["archivo_nombre"] = ""
        if actual.get("tipo") == "tts" and actual.get("texto") == b["texto"] and (actual.get("voz") or "") == b["voz"] \
                and viejo and (carpeta() / viejo).is_file() and not datos.get("rehacer_voz"):
            b["duracion"] = actual["duracion"]
        else:
            nuevo, b["duracion"] = _voz(b["texto"], settings.load(), b["voz"])
    if nuevo:
        b["archivo"] = nuevo
    if "duracion" in b:
        b["duracion"] = round(float(b["duracion"] or 0), 2)
    b["modificado"] = _ahora()
    try:
        if bid:
            db.execute("UPDATE biblioteca SET {} WHERE id=?".format(", ".join("{}=?".format(k) for k in b)),
                       list(b.values()) + [bid])
        else:
            b["creado"], b["creado_por"] = b["modificado"], usuario
            bid = db.execute("INSERT INTO biblioteca ({}) VALUES ({})".format(", ".join(b), ", ".join("?" * len(b))),
                             list(b.values()))
    except Exception:
        if nuevo:
            paths.rm(carpeta() / nuevo)
        raise
    if nuevo and viejo:
        paths.rm(carpeta() / viejo)
    log.info("%s %s «%s» en la biblioteca", usuario or "?", "editó" if actual else "agregó", b["nombre"])
    return uno(bid)


def varios_txt(archivos, usuario="", voz=None):
    """«Cargar varios .txt»: una entrada por archivo [{nombre, texto}], con el nombre del archivo.
    Devuelve [{nombre, ok, error|id}]. Sigue con los demás si uno falla."""
    if not isinstance(archivos, list) or not archivos:
        raise ValueError("No llegó ningún archivo")
    if len(archivos) > MAX_TXT_LOTE:
        raise ValueError("Máximo {} archivos a la vez".format(MAX_TXT_LOTE))
    out = []
    for f in archivos:
        nombre = os.path.splitext(str((f or {}).get("nombre") or "texto").strip())[0][:80] or "texto"
        try:
            b = guardar({"nombre": nombre, "tipo": "tts", "texto": (f or {}).get("texto"), "voz": voz or {}}, usuario=usuario)
            out.append({"nombre": nombre, "ok": True, "id": b["id"], "duracion": b["duracion"]})
        except Exception as e:
            out.append({"nombre": nombre, "ok": False, "error": str(e)[:200]})
    return out


def duplicar(bid, usuario=""):
    b = uno(bid)
    nuevo = ""
    if b["archivo"] and (carpeta() / b["archivo"]).is_file():
        nuevo = "bi_{}.wav".format(uuid.uuid4().hex[:10])
        shutil.copyfile(str(carpeta() / b["archivo"]), str(carpeta() / nuevo))
    c = {k: b[k] for k in ("notas", "tipo", "texto", "voz", "archivo_nombre", "duracion")}
    c.update(nombre=(b["nombre"] + " (copia)")[:80], archivo=nuevo, creado=_ahora(), modificado=_ahora(), creado_por=usuario)
    bid2 = db.execute("INSERT INTO biblioteca ({}) VALUES ({})".format(", ".join(c), ", ".join("?" * len(c))), list(c.values()))
    log.info("%s duplicó «%s» en la biblioteca", usuario, b["nombre"])
    return uno(bid2)


def borrar(bid, usuario=""):
    b = uno(bid)
    db.execute("DELETE FROM biblioteca WHERE id=?", (bid,))
    if b["archivo"]:
        paths.rm(carpeta() / b["archivo"])
    log.info("%s borró «%s» de la biblioteca", usuario, b["nombre"])


def copiar_a(b, carpeta_destino, prefijo="an_"):
    """Copia el audio de la biblioteca a otra carpeta (al programar un anuncio). Devuelve el nombre nuevo."""
    p = ruta(b)
    if not p or not p.is_file():
        raise ValueError("Ese audio de la biblioteca ya no tiene archivo")
    nombre = "{}{}.wav".format(prefijo, uuid.uuid4().hex[:10])
    shutil.copyfile(str(p), str(carpeta_destino / nombre))
    return nombre


def transmitir(bid, destino, usuario=""):
    """Una sola vez, por la cola de los anuncios (espera canal libre)."""
    b = uno(bid)
    p = ruta(b)
    con_vars = b["tipo"] == "tts" and anuncios._tiene_variables(b["texto"])
    if not con_vars and (not p or not p.is_file()):
        raise ValueError("Ese audio no tiene archivo; edítalo y guárdalo otra vez")
    ok = anuncios.emisor.encolar_audio({"clave": "bib:{}".format(bid), "nombre": "📚 " + b["nombre"],
                                        "texto": b["texto"] if con_vars else "", "wav": str(p) if not con_vars else "",
                                        "voz": b["voz"]}, "biblioteca · " + usuario, destino)
    if not ok:
        raise ValueError("Ese audio ya está en espera o al aire")
    log.info("%s mandó al aire «%s» de la biblioteca", usuario, b["nombre"])


class _Subida:
    """Lo que espera app._reemplazar_audio (como un archivo subido), con una copia del audio de la biblioteca."""
    def __init__(self, path, filename):
        self.path, self.filename = path, filename


def como_subida(bid):
    """Para usar un audio de la biblioteca en una sección: una copia en tmp/ que la sección se queda."""
    b = uno(bid)
    p = ruta(b)
    if not p or not p.is_file():
        raise ValueError("Ese audio de la biblioteca ya no tiene archivo")
    tmp = paths.tmp_dir() / "bi_sec_{}.wav".format(uuid.uuid4().hex[:8])
    shutil.copyfile(str(p), str(tmp))
    return b, _Subida(str(tmp), (b["nombre"] or "biblioteca") + ".wav")


def a_secciones():
    """Cada audio de la biblioteca pasa a ser una sección sin evento (texto → voz conserva texto y voz;
    lo demás, como sección de audio). El archivo se mueve a audios/. Devuelve cuántos pasó."""
    import re
    import time
    n = 0
    try:
        items = db.rows("SELECT * FROM biblioteca ORDER BY id")
    except Exception:
        return 0
    for b in items:
        p = ruta(b)
        try:
            sid = db.insert_seccion(b["nombre"], "TTS" if b["tipo"] == "tts" else "Audio",
                                    texto_tts=b["texto"] if b["tipo"] == "tts" else None,
                                    descripcion=b.get("notas") or None)
            campos = {"voz": b.get("voz") or ""}
            if p and p.is_file():
                stem = re.sub(r"[^A-Za-z0-9_-]+", "_", b["nombre"]).strip("_")[:50] or "audio"
                dest = paths.audios_dir() / "{}_{}.wav".format(sid, stem)
                shutil.move(str(p), str(dest))
                campos.update(ruta_archivo=dest.name, duracion=b["duracion"], audio_ts=time.time())
            db.update_seccion(sid, **campos)
            db.execute("DELETE FROM biblioteca WHERE id=?", (b["id"],))
            n += 1
        except Exception:
            log.exception("No pude pasar «%s» de la biblioteca a Secciones", b["nombre"])
    if n:
        log.info("Biblioteca: %d audios pasaron a Secciones (sin evento)", n)
    return n
