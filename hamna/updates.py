"""
HAMNA Web — buscar actualizaciones en GitHub.

Solo cuentan las VERSIONES PUBLICADAS: etiquetas vX.Y.Z del repositorio. Lo
que se sube a main sin etiqueta (cambios en prueba) no aparece como
actualización. La lista de cambios son los commits entre la versión
instalada y la última. La respuesta se guarda 6 horas (GitHub permite 60
consultas por hora sin cuenta).
"""
import json
import logging
import re
import threading
import time
import urllib.request

from . import VERSION, settings

log = logging.getLogger("hamna.updates")

REPO_DEFAULT = "xe2mbe/hamna"
CACHE_SECS = 6 * 3600
TAG_RX = re.compile(r"^v(\d+\.\d+(?:\.\d+)?)$")
_lock = threading.Lock()
_cache = {"t": 0.0, "repo": None, "data": None}


def _get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "HAMNA-Web/" + VERSION,
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def vtuple(v):
    try:
        return tuple(int(x) for x in str(v).strip().lstrip("v").split("."))
    except ValueError:
        return (0,)


def check(force=False):
    repo = (settings.get("update_repo") or REPO_DEFAULT).strip()
    if not re.match(r"^[\w.-]+/[\w.-]+$", repo):
        raise ValueError("Repositorio inválido: " + repo)
    now = time.time()
    with _lock:
        if not force and _cache["data"] and _cache["repo"] == repo and now - _cache["t"] < CACHE_SECS:
            return dict(_cache["data"], instalada=VERSION)
    api = "https://api.github.com/repos/" + repo
    try:
        tags = json.loads(_get(api + "/tags?per_page=100"))
    except Exception as e:
        raise RuntimeError("No pude consultar GitHub: {}".format(e))
    versions = [t["name"] for t in tags if isinstance(t, dict) and TAG_RX.match(t.get("name", ""))]
    ultima = max(versions, key=vtuple)[1:] if versions else None
    hay = bool(ultima) and vtuple(ultima) > vtuple(VERSION)
    cambios = []
    if hay:
        try:
            base = "v" + VERSION if ("v" + VERSION) in versions else None
            if base:
                cmp_ = json.loads(_get("{}/compare/{}...v{}".format(api, base, ultima)))
                commits = list(reversed(cmp_.get("commits") or []))
            else:
                commits = json.loads(_get("{}/commits?sha=v{}&per_page=30".format(api, ultima)))
            for c in commits[:40]:
                msg = (c.get("commit", {}).get("message") or "").strip()
                cambios.append({"sha": (c.get("sha") or "")[:7], "titulo": msg.splitlines()[0] if msg else "",
                                "fecha": (c.get("commit", {}).get("committer", {}).get("date") or "")[:10]})
        except Exception as e:
            log.warning("No pude leer la lista de cambios: %s", e)
    data = {"repo": repo, "url": "https://github.com/" + repo, "ultima": ultima,
            "notas": "https://github.com/{}/releases/tag/v{}".format(repo, ultima) if ultima else "",
            "hay_actualizacion": hay, "cambios": cambios, "consultado": time.strftime("%Y-%m-%d %H:%M")}
    with _lock:
        _cache.update(t=now, repo=repo, data=data)
    return dict(data, instalada=VERSION)
