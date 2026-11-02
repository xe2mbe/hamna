"""Arranque: python3 -m hamna [--host 0.0.0.0] [--port 8090]"""
from __future__ import annotations

import argparse
import getpass
import logging
import logging.handlers
import sys
import threading

from . import VERSION, paths, settings


def setup_logging():
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(str(paths.log_file()), maxBytes=2_000_000,
                                              backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)


def set_password(pw: str | None):
    from werkzeug.security import generate_password_hash
    if not pw:
        pw = getpass.getpass("Contraseña nueva para HAMNA Web: ")
        if pw != getpass.getpass("Repítela: "):
            sys.exit("No coinciden.")
    if len(pw) < 6:
        sys.exit("Debe tener al menos 6 caracteres.")
    settings.save({"password_hash": generate_password_hash(pw, method="pbkdf2:sha256")})
    print("Contraseña guardada.")


def main():
    ap = argparse.ArgumentParser(prog="hamna-web")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--set-password", nargs="?", const="", metavar="CLAVE",
                    help="cambia la contraseña y sale")
    ap.add_argument("--init", nargs="*", metavar="clave=valor",
                    help="guarda ajustes iniciales y sale (lo usa el instalador)")
    a = ap.parse_args()

    if a.set_password is not None:
        set_password(a.set_password or None)
        return
    if a.init is not None:
        upd = dict(kv.split("=", 1) for kv in a.init if "=" in kv)
        cur = settings.load()
        settings.save({k: v for k, v in upd.items() if not cur.get(k)})
        return

    setup_logging()
    from .app import app, init_app
    from .engine import engine
    init_app()
    logging.getLogger("hamna").info("HAMNA Web %s en http://%s:%d  datos=%s",
                                    VERSION, a.host, a.port, paths.data_dir())
    threading.Thread(target=engine.scheduler_loop, daemon=True).start()
    try:
        from waitress import serve
        serve(app, host=a.host, port=a.port, threads=8, channel_timeout=600,
              max_request_body_size=300 * 1024 * 1024, ident="HAMNA")
    except ImportError:
        app.run(host=a.host, port=a.port, threaded=True)


if __name__ == "__main__":
    main()
