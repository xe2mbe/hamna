"""Arranque: python3 -m hamna [--host 0.0.0.0] [--port 8090]"""
import argparse
import getpass
import io
import json
import logging
import logging.handlers
import sys
import threading

from . import VERSION, paths, settings


def setup_logging():
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(str(paths.log_file()), maxBytes=2000000,
                                              backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)


def set_password(pw, usuario, create=False):
    """hamna-web-passwd. A user that does not exist is only created when it is
    "admin", when --create is given, or after confirming it at the terminal:
    this avoids creating an administrator named after a mistyped password."""
    from . import auth
    if not auth.user_exists(usuario) and usuario != "admin" and not create:
        if not sys.stdin.isatty():
            sys.exit("User '{}' does not exist. Use --create to create it as administrator.".format(usuario))
        ans = input("User '{}' does not exist. Create it as administrator? [y/N] ".format(usuario))
        if ans.strip().lower() not in ("y", "yes", "s", "si"):
            sys.exit("Nothing changed.")
    if not pw:
        pw = getpass.getpass("New password for HAMNA Web user '{}': ".format(usuario))
        if pw != getpass.getpass("Repeat it: "):
            sys.exit("The passwords do not match. Nothing changed.")
    try:
        res = auth.set_password_cli(usuario, pw)
    except ValueError as e:
        sys.exit(str(e))
    print("User '{}': {}.".format(usuario, res))


def utf8_stdio():
    """HamVOIP solo tiene el idioma C (ASCII): con Python 3.5 un print con
    acentos truena. Forzar UTF-8 en la salida y en la entrada."""
    for name in ("stdout", "stderr"):
        st = getattr(sys, name)
        if st and (st.encoding or "").lower().replace("-", "") != "utf8":
            setattr(sys, name, io.TextIOWrapper(st.buffer, encoding="utf-8",
                                                errors="replace", line_buffering=True))


def main():
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="hamna-web")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--set-password", nargs="?", const="", metavar="PASSWORD",
                    help="cambia la contraseña y sale")
    ap.add_argument("--init", nargs="*", metavar="clave=valor",
                    help="guarda ajustes iniciales que aún no existan y sale (instalador)")
    ap.add_argument("--user", default="admin", metavar="USER",
                    help="user for --set-password (default admin)")
    ap.add_argument("--create", action="store_true",
                    help="with --set-password: create the user as administrator if it does not exist")
    ap.add_argument("--has-password", action="store_true", help="sale con 0 si ya hay un administrador")
    a = ap.parse_args()

    if a.set_password is not None:
        set_password(a.set_password or None, a.user, a.create)
        return
    if a.has_password:
        from . import auth
        sys.exit(0 if auth.has_admin() else 1)
    if a.init is not None:
        upd = dict(kv.split("=", 1) for kv in a.init if "=" in kv)
        stored = {}
        if paths.settings_file().is_file():
            stored = json.loads(paths.settings_file().read_text(encoding="utf-8"))
        settings.save({k: v for k, v in upd.items() if v and not stored.get(k)})
        return

    setup_logging()
    from .app import app, init_app
    from .engine import engine
    init_app()
    logging.getLogger("hamna").info("HAMNA Web %s · Python %s · datos en %s",
                                    VERSION, sys.version.split()[0], paths.data_dir())
    threading.Thread(target=engine.scheduler_loop, daemon=True).start()
    from . import health
    health.start()
    from .live import live
    live.start()
    app.serve(a.host, a.port)


if __name__ == "__main__":
    main()
