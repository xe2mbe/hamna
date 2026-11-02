"""Rutas de datos. Todo vive bajo HAMNA_DATA (por defecto /var/lib/hamna)."""
from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    d = Path(os.environ.get("HAMNA_DATA", "/var/lib/hamna"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sub(name: str) -> Path:
    d = data_dir() / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_file() -> Path:
    return data_dir() / "hamna.db"


def settings_file() -> Path:
    return data_dir() / "settings.json"


def audios_dir() -> Path:      # originales subidos y TTS generados
    return _sub("audios")


def sonidos_dir() -> Path:     # audios de pausa (alerta, pausa, continuamos)
    return _sub("sonidos")


def cache_dir() -> Path:       # audios ya convertidos a 8 kHz y normalizados
    return _sub("cache")


def tmp_dir() -> Path:         # tramos al aire y pruebas; se limpia solo
    return _sub("tmp")


def log_file() -> Path:
    return data_dir() / "hamna.log"
