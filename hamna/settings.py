"""Ajustes en JSON (settings.json en la carpeta de datos)."""
import json
import os
import threading

from . import paths

DEFAULTS = {
    # Nodo
    "backend": "auto",          # auto | asl | irlp | simulado
    "node": "",                 # número de nodo ASL o stationid IRLP
    "asl_mode": "localplay",    # localplay (solo el nodo) | playback (nodo + enlazados)
    # Cortar el audio al pulsar Detener/Siguiente: COP 24 vacía la cola de
    # telemetría de app_rpt (probado en HamVOIP). {nodo} = número de nodo.
    "asl_flush_cmd": "rpt cmd {nodo} cop 24 0",
    "irlp_env": "/home/irlp/custom/environment",
    "irlp_key_cmd": "key",
    "irlp_unkey_cmd": "unkey",
    "irlp_player": "aplay",
    "station_name": "",

    # TTS
    "tts_engine": "azure",      # azure | piper | espeak
    "azure_key": "",
    "azure_region": "eastus",
    "azure_voice": "es-MX-DaliaNeural",
    "azure_style": "general",
    "azure_rate": 100,
    "azure_pitch": 0,
    "espeak_voice": "es-419",
    "espeak_speed": 150,
    "espeak_pitch": 50,

    # Tiempos y pausas (mismos nombres que HAMNA Desktop)
    "pause_enabled": False,
    "pause_tx_time": 160,
    "pause_duration": 10,
    "pause_alert_before": 10,
    "pause_alert_file": "",
    "pause_announcement_file": "",
    "pause_resume_file": "",
    "ptt_on_delay": 0.5,
    "retroceso_enabled": False,
    "retroceso_secs": 5,
    "section_gap": 3,

    # Normalización
    "section_normalize": True,
    "normalize_target": -18.0,
    "pause_volume": 95,

    # Seguridad
    "password_hash": "",
    "secret_key": "",
}

# Claves que nunca se mandan al navegador
SECRET_KEYS = {"password_hash", "secret_key", "azure_key"}

_lock = threading.Lock()
_cache = None


def load():
    global _cache
    with _lock:
        if _cache is None:
            data = {}
            f = paths.settings_file()
            if f.is_file():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            _cache = {**DEFAULTS, **data}
        return dict(_cache)


def get(key, default=None):
    return load().get(key, DEFAULTS.get(key, default))


def save(updates):
    global _cache
    cfg = load()
    cfg.update(updates)
    with _lock:
        f = paths.settings_file()
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(f))
        try:
            os.chmod(str(f), 0o600)
        except OSError:
            pass
        _cache = cfg
    return dict(cfg)


def public():
    cfg = load()
    out = {k: v for k, v in cfg.items() if k not in SECRET_KEYS}
    out["azure_key_set"] = bool(cfg.get("azure_key"))
    return out
