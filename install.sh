#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  HAMNA Web — instalador para nodos AllStarLink (ASL3, ASL2, HamVOIP) e IRLP
#
#  Uso:   sudo ./install.sh [opciones]
#
#    --tipo asl|irlp      forzar el tipo de nodo (por defecto se detecta)
#    --nodo NUMERO        número de nodo (ASL) o stationid (IRLP)
#    --puerto 8090        puerto de la página web
#    --password CLAVE     contraseña de la página (si no, se pregunta)
#    --sin-paquetes       no instalar nada con apt (ffmpeg, espeak-ng)
#    --sin-cron           no dar permiso a la página para ver/editar el cron
#
#  No necesita paquetes de Python: usa solo Python 3.5 o más nuevo.
#  Volver a ejecutarlo actualiza el programa y conserva los datos.
# ─────────────────────────────────────────────────────────────────────────────
set -eu

APP_DIR=/opt/hamna-web
DATA_DIR=/var/lib/hamna
SERVICE=hamna-web
PORT=8090
TIPO=""
NODO=""
PASSWORD=""
APT=1
CRON=1
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONIOENCODING=utf-8

c_ok()   { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }
c_info() { printf '\033[1;34m[..]\033[0m %s\n' "$*"; }
c_warn() { printf '\033[1;33m[!!]\033[0m %s\n' "$*"; }
die()    { printf '\033[1;31m[XX] %s\033[0m\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --tipo) TIPO="$2"; shift 2 ;;
    --nodo) NODO="$2"; shift 2 ;;
    --puerto) PORT="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --sin-paquetes) APT=0; shift ;;
    --sin-cron) CRON=0; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) die "Opción desconocida: $1" ;;
  esac
done

[ "$(id -u)" -eq 0 ] || die "Ejecútalo como root:  sudo $0"
[ -f "$SRC_DIR/hamna/__main__.py" ] || die "No encuentro el código (carpeta hamna/) junto a install.sh"

echo
echo "  HAMNA Web - instalación"
echo "  -----------------------"

# ── 1. Tipo de nodo ─────────────────────────────────────────────────────────
AST=$(command -v asterisk 2>/dev/null || ls /usr/sbin/asterisk /usr/local/sbin/asterisk 2>/dev/null | head -1 || true)
if [ -z "$TIPO" ]; then
  if [ -d /home/irlp/scripts ] || [ -f /home/irlp/custom/environment ]; then
    TIPO=irlp
  elif [ -f /etc/asterisk/rpt.conf ] && [ -n "$AST" ]; then
    TIPO=asl
  else
    die "No detecté AllStarLink ni IRLP. Usa --tipo asl o --tipo irlp"
  fi
fi
case "$TIPO" in asl|irlp) ;; *) die "--tipo debe ser asl o irlp" ;; esac

SABOR=""
if [ "$TIPO" = asl ]; then
  if [ -f /usr/local/etc/allstar.env ] || [ -d /usr/local/hamvoip-sbin ]; then SABOR=HamVOIP
  elif dpkg -s asl3 >/dev/null 2>&1; then SABOR="AllStarLink 3"
  else SABOR=AllStarLink; fi
  # El servicio corre con el mismo usuario que Asterisk (asterisk en ASL3, root en HamVOIP)
  RUN_USER=$(ps -o user= -C asterisk 2>/dev/null | head -1 | tr -d ' ' || true)
  [ -n "$RUN_USER" ] || { id asterisk >/dev/null 2>&1 && RUN_USER=asterisk || RUN_USER=root; }
  if [ -z "$NODO" ]; then
    NODO=$(grep -m1 -E '^\[[0-9]{3,7}\]' /etc/asterisk/rpt.conf | sed 's/^\[\([0-9]*\)\].*/\1/' || true)
  fi
  c_ok "$SABOR, nodo ${NODO:-?} (servicio como $RUN_USER)"
else
  SABOR=IRLP
  RUN_USER=repeater
  id repeater >/dev/null 2>&1 || die "No existe el usuario 'repeater' de IRLP"
  if [ -z "$NODO" ]; then
    NODO=$(bash -c '. /home/irlp/custom/environment 2>/dev/null; echo "${STATIONID:-}"' || true)
  fi
  c_ok "IRLP ${NODO:-?} (servicio como $RUN_USER)"
fi
RUN_GROUP=$(id -gn "$RUN_USER")
HAS_IRLP=0; [ -d /home/irlp/scripts ] && id repeater >/dev/null 2>&1 && HAS_IRLP=1
HAS_ASL=0; [ -f /etc/asterisk/rpt.conf ] && [ -n "$AST" ] && HAS_ASL=1
[ "$HAS_IRLP" = 1 ] && [ "$HAS_ASL" = 1 ] && c_ok "Este nodo tiene ASL e IRLP: se podrán programar conexiones en los dos"

# ── 2. Python y herramientas de audio ───────────────────────────────────────
PY=$(command -v python3 || true)
[ -n "$PY" ] || die "Falta python3"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 5) else 1)' || die "Se necesita Python 3.5 o más nuevo"
c_ok "$("$PY" --version 2>&1)"

if [ "$APT" = 1 ] && command -v apt-get >/dev/null 2>&1; then
  PKGS="ffmpeg espeak-ng"
  [ "$TIPO" = irlp ] && PKGS="$PKGS alsa-utils"
  MISSING=""
  # Se busca el comando, no el paquete: asl3-tts trae su propio espeak-ng
  # (y su libespeak-ng), y el paquete de Debian choca con él.
  for p in $PKGS; do
    c=$p; [ "$p" = alsa-utils ] && c=aplay
    command -v "$c" >/dev/null 2>&1 || dpkg -s "$p" >/dev/null 2>&1 || MISSING="$MISSING $p"
  done
  if dpkg -s asl3-tts >/dev/null 2>&1; then MISSING=$(echo "$MISSING" | sed 's/ espeak-ng//'); fi
  if [ -n "$MISSING" ]; then
    c_info "Instalando:$MISSING (puede tardar unos minutos)"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null 2>&1 || c_warn "apt-get update tuvo errores; sigo"
    # shellcheck disable=SC2086
    apt-get install -y -qq --no-install-recommends $MISSING >/dev/null 2>&1 \
      || c_warn "No se pudo instalar:$MISSING (HAMNA funciona con lo que haya)"
  fi
elif [ "$SABOR" = HamVOIP ]; then
  c_info "HamVOIP: no se instala nada con pacman; uso sox y mpg123 del sistema"
fi
if command -v ffmpeg >/dev/null 2>&1; then
  c_ok "Audio con ffmpeg (todos los formatos, nivel en LUFS)"
elif command -v sox >/dev/null 2>&1; then
  command -v mpg123 >/dev/null 2>&1 && MP3=" y MP3 con mpg123" || MP3=" (sin MP3: falta mpg123)"
  c_ok "Audio con sox$MP3"
else
  die "No hay ffmpeg ni sox para convertir audio"
fi

# ── 3. Programa y datos ─────────────────────────────────────────────────────
systemctl stop "$SERVICE" 2>/dev/null || true
mkdir -p "$APP_DIR" "$DATA_DIR"
rm -rf "$APP_DIR/hamna"
cp -r "$SRC_DIR/hamna" "$APP_DIR/"
rm -rf "$APP_DIR/bin" && mkdir -p "$APP_DIR/bin"
cp "$SRC_DIR"/bin/hamna-* "$APP_DIR/bin/"
sed -i "1s|.*|#!$PY -I|" "$APP_DIR/bin/hamna-cron"
for f in install.sh uninstall.sh README.md; do [ -f "$SRC_DIR/$f" ] && cp "$SRC_DIR/$f" "$APP_DIR/"; done
find "$APP_DIR" -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
chown -R root:root "$APP_DIR"
chmod -R a+rX "$APP_DIR"
chmod 755 "$APP_DIR"/*.sh "$APP_DIR"/bin/* 2>/dev/null || true
chmod 755 "$APP_DIR" "$APP_DIR/bin"
chown -R "$RUN_USER:$RUN_GROUP" "$DATA_DIR"
chmod 750 "$DATA_DIR"
[ "$TIPO" = irlp ] && { usermod -aG audio repeater 2>/dev/null || true; }
c_ok "Programa en $APP_DIR, datos en $DATA_DIR"

run_as() { if [ "$RUN_USER" = root ]; then "$@"; else runuser -u "$RUN_USER" -- "$@"; fi; }
hamna() { (cd "$APP_DIR" && run_as env HAMNA_DATA="$DATA_DIR" PYTHONIOENCODING=utf-8 "$PY" -m hamna "$@"); }

TTS=azure
command -v espeak-ng >/dev/null 2>&1 && TTS=espeak
command -v asl-tts >/dev/null 2>&1 && TTS=piper
hamna --init "backend=$TIPO" "node=$NODO" "tts_engine=$TTS"

# ── 4. Usuario administrador ────────────────────────────────────────────────
if [ -n "$PASSWORD" ]; then
  hamna --set-password "$PASSWORD" >/dev/null
  c_ok "Usuario admin listo"
elif hamna --has-password; then
  c_ok "Se conservan los usuarios actuales"
elif [ -t 0 ]; then
  while :; do
    printf "  Contraseña del usuario admin de la página: "; stty -echo; read -r P1; stty echo; echo
    printf "  Repítela: "; stty -echo; read -r P2; stty echo; echo
    [ "$P1" = "$P2" ] && [ ${#P1} -ge 6 ] && break
    c_warn "No coinciden o tiene menos de 6 caracteres"
  done
  hamna --set-password "$P1" >/dev/null
  c_ok "Usuario admin listo"
else
  P1=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 10)
  hamna --set-password "$P1" >/dev/null
  c_warn "Usuario: admin   Contraseña generada: $P1   (cámbiala en Ajustes > Mi cuenta)"
fi

if [ "$RUN_USER" = root ]; then RUNPFX=""; else RUNPFX="runuser -u $RUN_USER --"; fi
cat > /usr/local/bin/hamna-web-passwd <<EOF
#!/bin/sh
# Cambia la contraseña de un usuario de HAMNA Web (admin si no se indica otro).
# Uso: hamna-web-passwd [--user USUARIO] [CLAVE]   Si el usuario no existe, se crea como administrador.
cd $APP_DIR && exec $RUNPFX env HAMNA_DATA=$DATA_DIR PYTHONIOENCODING=utf-8 $PY -m hamna --set-password "\$@"
EOF
chmod 755 /usr/local/bin/hamna-web-passwd

# ── 4b. Permisos para cron y conexiones ─────────────────────────────────────
# Reglas de sudo limitadas a los ayudantes fijos de /opt/hamna-web/bin
# (dueño root, sin escritura para el servicio).
SUDOERS=/etc/sudoers.d/hamna-web
rm -f "$SUDOERS"
if [ "$RUN_USER" != root ] && command -v sudo >/dev/null 2>&1 && [ -d /etc/sudoers.d ]; then
  TMP=$(mktemp)
  echo "# HAMNA Web (lo crea install.sh; se borra con uninstall.sh)" > "$TMP"
  [ "$CRON" = 1 ] && echo "$RUN_USER ALL=(root) NOPASSWD: $APP_DIR/bin/hamna-cron" >> "$TMP"
  [ "$HAS_IRLP" = 1 ] && [ "$RUN_USER" != repeater ] &&     echo "$RUN_USER ALL=(repeater) NOPASSWD: $APP_DIR/bin/hamna-irlp" >> "$TMP"
  if [ "$HAS_ASL" = 1 ] && [ "$TIPO" = irlp ]; then
    AST_USER=$(ps -o user= -C asterisk 2>/dev/null | head -1 | tr -d ' ' || true)
    [ -n "$AST_USER" ] && [ "$AST_USER" != "$RUN_USER" ] &&       echo "$RUN_USER ALL=($AST_USER) NOPASSWD: $AST -rx *" >> "$TMP"
  fi
  if [ "$(wc -l < "$TMP")" -gt 1 ]; then
    if visudo -cf "$TMP" >/dev/null 2>&1; then
      install -m 440 -o root -g root "$TMP" "$SUDOERS"
      c_ok "Permisos de sudo para cron/conexiones en $SUDOERS"
    else
      c_warn "No pude validar la regla de sudo; la página no podrá editar el cron"
    fi
  fi
  rm -f "$TMP"
elif [ "$RUN_USER" != root ]; then
  c_warn "Sin sudo: la página no podrá ver el cron de root"
fi

# ── 5. Servicio ─────────────────────────────────────────────────────────────
AFTER="network-online.target"
[ "$TIPO" = asl ] && systemctl cat asterisk >/dev/null 2>&1 && AFTER="$AFTER asterisk.service"
{
  echo "[Unit]"
  echo "Description=HAMNA Web - automatizacion de redes ($SABOR)"
  echo "After=$AFTER"
  echo "Wants=network-online.target"
  echo
  echo "[Service]"
  echo "Type=simple"
  echo "User=$RUN_USER"
  [ "$TIPO" = irlp ] && echo "SupplementaryGroups=audio"
  echo "WorkingDirectory=$APP_DIR"
  echo "Environment=HAMNA_DATA=$DATA_DIR"
  echo "Environment=PYTHONIOENCODING=utf-8"
  echo "Environment=PYTHONUNBUFFERED=1"
  echo "ExecStart=$PY -m hamna --host 0.0.0.0 --port $PORT"
  echo "Restart=on-failure"
  echo "RestartSec=5"
  echo
  echo "[Install]"
  echo "WantedBy=multi-user.target"
} > /etc/systemd/system/$SERVICE.service
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null 2>&1
systemctl restart "$SERVICE"
sleep 3
systemctl is-active --quiet "$SERVICE" || { journalctl -u "$SERVICE" -n 30 --no-pager; die "El servicio no arrancó"; }
c_ok "Servicio $SERVICE activo"

# ── 6. Firewall ─────────────────────────────────────────────────────────────
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  ZONE=$(firewall-cmd --get-default-zone)
  firewall-cmd -q --zone="$ZONE" --add-port="$PORT"/tcp --permanent && firewall-cmd -q --reload
  c_ok "Puerto $PORT abierto en firewalld (zona $ZONE)"
elif command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow "$PORT"/tcp >/dev/null && c_ok "Puerto $PORT abierto en ufw"
fi

# ── 7. Listo ────────────────────────────────────────────────────────────────
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
[ -n "$IP" ] || IP=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -1)
echo
c_ok "HAMNA Web instalado"
echo
echo "   Abre en el navegador:  http://${IP:-IP-DEL-NODO}:$PORT"
echo
echo "   Entrar con:            usuario admin"
echo "   Cambiar contraseña:    hamna-web-passwd [--user USUARIO]"
echo "   Ver bitácora:          journalctl -u $SERVICE -f"
echo "   Desinstalar:           $APP_DIR/uninstall.sh"
echo
