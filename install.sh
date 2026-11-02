#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  HAMNA Web — instalador para nodos AllStarLink (ASL3 / ASL2 / HamVOIP) e IRLP
#
#  Uso:   sudo ./install.sh [opciones]
#
#    --tipo asl|irlp      forzar el tipo de nodo (por defecto se detecta)
#    --nodo NUMERO        número de nodo (ASL) o stationid (IRLP)
#    --puerto 8090        puerto de la página web
#    --password CLAVE     contraseña de la página (si no, se pregunta)
#    --sin-espeak         no instalar espeak-ng
#
#  Volver a ejecutarlo actualiza el programa y conserva los datos.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR=/opt/hamna-web
DATA_DIR=/var/lib/hamna
SERVICE=hamna-web
PORT=8090
TIPO=""
NODO=""
PASSWORD=""
ESPEAK=1
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

c_ok()   { printf '\033[1;32m✔\033[0m %s\n' "$*"; }
c_info() { printf '\033[1;34m•\033[0m %s\n' "$*"; }
c_warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }
die()    { printf '\033[1;31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --tipo) TIPO="$2"; shift 2 ;;
    --nodo) NODO="$2"; shift 2 ;;
    --puerto) PORT="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --sin-espeak) ESPEAK=0; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) die "Opción desconocida: $1" ;;
  esac
done

[ "$(id -u)" -eq 0 ] || die "Ejecútalo con sudo:  sudo $0"
[ -f "$SRC_DIR/hamna/__main__.py" ] || die "No encuentro el código (carpeta hamna/) junto a install.sh"

echo
echo "  HAMNA Web — instalación"
echo "  ───────────────────────"

# ── 1. Detectar el tipo de nodo ─────────────────────────────────────────────
if [ -z "$TIPO" ]; then
  if [ -d /home/irlp/scripts ] || [ -f /home/irlp/custom/environment ]; then
    TIPO=irlp
  elif [ -f /etc/asterisk/rpt.conf ] && { command -v asterisk >/dev/null || [ -x /usr/sbin/asterisk ]; }; then
    TIPO=asl
  else
    die "No detecté ASL ni IRLP. Usa --tipo asl o --tipo irlp"
  fi
fi
case "$TIPO" in asl|irlp) ;; *) die "--tipo debe ser asl o irlp" ;; esac

if [ "$TIPO" = asl ]; then
  RUN_USER=asterisk
  id asterisk >/dev/null 2>&1 || RUN_USER=root     # HamVOIP / ASL viejos corren Asterisk como root
  if [ -z "$NODO" ]; then
    NODO=$(grep -m1 -E '^\[[0-9]{3,7}\]' /etc/asterisk/rpt.conf | tr -d '[]' | awk '{print $1}' | sed 's/(.*//') || true
  fi
  c_ok "Nodo AllStarLink ${NODO:-?} (servicio como usuario $RUN_USER)"
else
  RUN_USER=repeater
  id repeater >/dev/null 2>&1 || die "No existe el usuario 'repeater' de IRLP"
  if [ -z "$NODO" ]; then
    NODO=$(bash -c '. /home/irlp/custom/environment 2>/dev/null; echo "${STATIONID:-}"') || true
  fi
  c_ok "Nodo IRLP ${NODO:-?} (servicio como usuario $RUN_USER)"
fi

# ── 2. Paquetes ─────────────────────────────────────────────────────────────
PKGS="python3 python3-flask ffmpeg"
apt-cache show python3-waitress >/dev/null 2>&1 && PKGS="$PKGS python3-waitress"
[ "$ESPEAK" = 1 ] && PKGS="$PKGS espeak-ng"
[ "$TIPO" = irlp ] && PKGS="$PKGS alsa-utils"
MISSING=""
for p in $PKGS; do dpkg -s "$p" >/dev/null 2>&1 || MISSING="$MISSING $p"; done
if [ -n "$MISSING" ]; then
  c_info "Instalando paquetes:$MISSING  (puede tardar unos minutos)"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq || c_warn "apt-get update tuvo errores; intento instalar de todos modos"
  # shellcheck disable=SC2086
  apt-get install -y -qq --no-install-recommends $MISSING >/dev/null || die "No se pudieron instalar:$MISSING"
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' || die "Se necesita Python 3.7 o más nuevo"
python3 -c 'import flask' || die "Flask no quedó instalado"
c_ok "Paquetes listos ($(python3 -c 'import flask; print("Flask", flask.__version__)' 2>/dev/null))"

# ── 3. Programa y datos ─────────────────────────────────────────────────────
systemctl stop "$SERVICE" 2>/dev/null || true
mkdir -p "$APP_DIR" "$DATA_DIR"
rm -rf "$APP_DIR/hamna"
cp -r "$SRC_DIR/hamna" "$APP_DIR/"
cp "$SRC_DIR/install.sh" "$SRC_DIR/uninstall.sh" "$APP_DIR/" 2>/dev/null || true
[ -f "$SRC_DIR/README.md" ] && cp "$SRC_DIR/README.md" "$APP_DIR/"
find "$APP_DIR" -name '__pycache__' -prune -exec rm -rf {} +
chown -R root:root "$APP_DIR"
chmod -R a+rX "$APP_DIR"
chown -R "$RUN_USER":"$(id -gn "$RUN_USER")" "$DATA_DIR"
chmod 750 "$DATA_DIR"
[ "$TIPO" = irlp ] && usermod -aG audio repeater 2>/dev/null || true
c_ok "Programa en $APP_DIR, datos en $DATA_DIR"

run_as() { if [ "$RUN_USER" = root ]; then "$@"; else runuser -u "$RUN_USER" -- "$@"; fi; }
HAMNA_PY() { (cd "$APP_DIR" && run_as env HAMNA_DATA="$DATA_DIR" python3 -m hamna "$@"); }

HAMNA_PY --init "backend=$TIPO" "node=$NODO"

# ── 4. Contraseña ───────────────────────────────────────────────────────────
HAS_PW=$(cd "$APP_DIR" && HAMNA_DATA="$DATA_DIR" python3 -c 'from hamna import settings; print(1 if settings.get("password_hash") else 0)')
if [ -n "$PASSWORD" ]; then
  HAMNA_PY --set-password "$PASSWORD" >/dev/null
  c_ok "Contraseña guardada"
elif [ "$HAS_PW" = 0 ]; then
  if [ -t 0 ]; then
    while :; do
      read -r -s -p "  Contraseña para entrar a la página: " P1; echo
      read -r -s -p "  Repítela: " P2; echo
      [ "$P1" = "$P2" ] && [ ${#P1} -ge 6 ] && break
      c_warn "No coinciden o tiene menos de 6 caracteres"
    done
    HAMNA_PY --set-password "$P1" >/dev/null
  else
    P1=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 10)
    HAMNA_PY --set-password "$P1" >/dev/null
    c_warn "Contraseña generada: $P1   (cámbiala en Ajustes → Seguridad)"
  fi
  c_ok "Contraseña guardada"
else
  c_ok "Se conserva la contraseña actual"
fi

# Comando para cambiarla después
cat > /usr/local/bin/hamna-web-passwd <<EOF
#!/bin/sh
# Cambia la contraseña de HAMNA Web
cd $APP_DIR && exec $( [ "$RUN_USER" = root ] && echo "" || echo "runuser -u $RUN_USER --") env HAMNA_DATA=$DATA_DIR python3 -m hamna --set-password "\$@"
EOF
chmod 755 /usr/local/bin/hamna-web-passwd

# ── 5. Servicio ─────────────────────────────────────────────────────────────
EXTRA_GROUPS=""
[ "$TIPO" = irlp ] && EXTRA_GROUPS="SupplementaryGroups=audio"
cat > /etc/systemd/system/$SERVICE.service <<EOF
[Unit]
Description=HAMNA Web - automatizacion de redes ($TIPO)
After=network-online.target$( [ "$TIPO" = asl ] && echo " asterisk.service" )
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
$EXTRA_GROUPS
WorkingDirectory=$APP_DIR
Environment=HAMNA_DATA=$DATA_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 -m hamna --host 0.0.0.0 --port $PORT
Restart=on-failure
RestartSec=5
Nice=-5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now "$SERVICE" >/dev/null 2>&1
sleep 3
systemctl is-active --quiet "$SERVICE" || { journalctl -u "$SERVICE" -n 30 --no-pager; die "El servicio no arrancó"; }
c_ok "Servicio $SERVICE activo"

# ── 6. Firewall ─────────────────────────────────────────────────────────────
if command -v firewall-cmd >/dev/null && firewall-cmd --state >/dev/null 2>&1; then
  ZONE=$(firewall-cmd --get-default-zone)
  firewall-cmd -q --zone="$ZONE" --add-port="$PORT"/tcp --permanent && firewall-cmd -q --reload
  c_ok "Puerto $PORT abierto en firewalld (zona $ZONE)"
elif command -v ufw >/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow "$PORT"/tcp >/dev/null && c_ok "Puerto $PORT abierto en ufw"
fi

# ── 7. Listo ────────────────────────────────────────────────────────────────
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
c_ok "HAMNA Web instalado"
echo
echo "   Abre en el navegador:  http://${IP:-IP-DEL-NODO}:$PORT"
echo
echo "   Cambiar contraseña:    sudo hamna-web-passwd"
echo "   Ver bitácora:          journalctl -u $SERVICE -f"
echo "   Desinstalar:           sudo $APP_DIR/uninstall.sh"
echo
