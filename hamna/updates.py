"""
HAMNA Web — buscar actualizaciones en GitHub.

Lee la versión publicada (hamna/__init__.py de la rama main) y la lista de
commits del repositorio. La respuesta se guarda 6 horas para no consultar
de más (GitHub permite 60 consultas por hora sin cuenta).
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


VER_RX = re.compile(r"\(v(\d+\.\d+(?:\.\d+)?)\)")


def check(force=False):
    repo = (settings.get("update_repo") or REPO_DEFAULT).strip()
    if not re.match(r"^[\w.-]+/[\w.-]+$", repo):
        raise ValueError("Repositorio inválido: " + repo)
    now = time.time()
    with _lock:
        if not force and _cache["data"] and _cache["repo"] == repo and now - _cache["t"] < CACHE_SECS:
            return dict(_cache["data"], instalada=VERSION)
    base = "https://raw.githubusercontent.com/{}/main/hamna/__init__.py".format(repo)
    try:
        m = re.search(r'VERSION\s*=\s*"([^"]+)"', _get(base))
        ultima = m.group(1) if m else None
        commits = json.loads(_get("https://api.github.com/repos/{}/commits?per_page=40".format(repo)))
    except Exception as e:
        raise RuntimeError("No pude consultar GitHub: {}".format(e))
    cambios = []
    actual = vtuple(VERSION)
    for c in commits if isinstance(commits, list) else []:
        msg = (c.get("commit", {}).get("message") or "").strip()
        titulo = msg.splitlines()[0] if msg else ""
        mv = VER_RX.search(titulo)
        if mv and vtuple(mv.group(1)) <= actual:
            break                           # de aquí para atrás ya está instalado
        cambios.append({"sha": (c.get("sha") or "")[:7], "titulo": titulo,
                        "fecha": (c.get("commit", {}).get("committer", {}).get("date") or "")[:10],
                        "version": mv.group(1) if mv else ""})
    hay = bool(ultima) and vtuple(ultima) > actual
    data = {"repo": repo, "url": "https://github.com/" + repo, "ultima": ultima,
            "hay_actualizacion": hay, "cambios": cambios if hay else [],
            "consultado": time.strftime("%Y-%m-%d %H:%M")}
    with _lock:
        _cache.update(t=now, repo=repo, data=data)
    return dict(data, instalada=VERSION)
