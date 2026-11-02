"""Rutas de datos. Todo vive bajo HAMNA_DATA (por defecto /var/lib/hamna)."""
import os
from pathlib import Path


def data_dir():
    d = Path(os.environ.get("HAMNA_DATA", "/var/lib/hamna"))
    if not d.is_dir():
        os.makedirs(str(d), exist_ok=True)
    return d


def _sub(name):
    d = data_dir() / name
    if not d.is_dir():
        os.makedirs(str(d), exist_ok=True)
    return d


def db_file():
    return data_dir() / "hamna.db"


def settings_file():
    return data_dir() / "settings.json"


def audios_dir():      # originales subidos y TTS generados
    return _sub("audios")


def sonidos_dir():     # audios de pausa (alerta, pausa, continuamos)
    return _sub("sonidos")


def cache_dir():       # audios ya convertidos a 8 kHz y normalizados
    return _sub("cache")


def tmp_dir():         # tramos al aire, subidas y pruebas; se limpia solo
    return _sub("tmp")


def log_file():
    return data_dir() / "hamna.log"


def rm(path):
    """Borra un archivo si existe (Path.unlink(missing_ok) es de Python 3.8)."""
    try:
        os.remove(str(path))
    except FileNotFoundError:
        pass
