#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  HAMNA Web — installer for AllStarLink (ASL3, ASL2, HamVOIP) and IRLP nodes
#
#  Usage:   sudo ./install.sh [options]
#
#    --type asl|irlp      force the node type (detected by default)
#    --node NUMBER        node number (ASL) or stationid (IRLP)
#    --port 8090          web page port
#    --password PASS      password for the "admin" user (asked if missing)
#    --no-packages        do not install anything with apt (ffmpeg, espeak-ng)
#    --no-cron            do not let the page view/edit the cron table
#    --no-apache          do not publish the page at http(s)://<node>/hamna/
#    --force              install even if HAMNA is on air or preparing audio
#
#  No Python packages needed: only Python 3.5 or newer.
#  Running it again updates the program and keeps all data, users and settings.
#  (The old Spanish options --tipo, --nodo, --puerto, --sin-paquetes and
#   --sin-cron still work.)
# ─────────────────────────────────────────────────────────────────────────────
set -eu

APP_DIR=/opt/hamna-web
DATA_DIR=/var/lib/hamna
BACKUP_DIR=/var/backups/hamna
SERVICE=hamna-web
PORT=8090
TYPE=""
NODE=""
PASSWORD=""
KEPT_USERS=0
APT=1
CRON=1
APACHE=1
FORCE=0
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONIOENCODING=utf-8

c_ok()   { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }
c_info() { printf '\033[1;34m[..]\033[0m %s\n' "$*"; }
c_warn() { printf '\033[1;33m[!!]\033[0m %s\n' "$*"; }
die()    { printf '\033[1;31m[XX] %s\033[0m\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --type|--tipo) TYPE="$2"; shift 2 ;;
    --node|--nodo) NODE="$2"; shift 2 ;;
    --port|--puerto) PORT="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --no-packages|--sin-paquetes) APT=0; shift ;;
    --no-cron|--sin-cron) CRON=0; shift ;;
    --no-apache) APACHE=0; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) die "Unknown option: $1  (see --help)" ;;
  esac
done

[ "$(id -u)" -eq 0 ] || die "Run it as root:  sudo $0"
[ -f "$SRC_DIR/hamna/__main__.py" ] || die "Cannot find the program (hamna/ folder) next to install.sh"
NEW_VERSION=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$SRC_DIR/hamna/__init__.py")

echo
echo "  HAMNA Web ${NEW_VERSION} - install"
echo "  ------------------------------"

# ── 0. Never interrupt a broadcast ──────────────────────────────────────────
LOG="$DATA_DIR/hamna.log"
if [ "$FORCE" = 0 ] && systemctl is-active --quiet "$SERVICE" 2>/dev/null; then
  if pgrep -x ffmpeg >/dev/null 2>&1 || pgrep -x sox >/dev/null 2>&1; then
    die "HAMNA is preparing audio right now. Try again in a few minutes (or use --force)."
  fi
  if [ -f "$LOG" ]; then
    last_start=$(grep -an "Iniciando «" "$LOG" | tail -1 | cut -d: -f1)
    last_end=$(grep -anE "» terminó|Transmisión detenida" "$LOG" | tail -1 | cut -d: -f1)
    if [ -n "$last_start" ] && [ "${last_end:-0}" -lt "$last_start" ]; then
      die "HAMNA is on air right now. Try again when the broadcast ends (or use --force)."
    fi
  fi
fi
OLD_VERSION=""
[ -f "$APP_DIR/hamna/__init__.py" ] && OLD_VERSION=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$APP_DIR/hamna/__init__.py")
[ -n "$OLD_VERSION" ] && c_info "Updating from ${OLD_VERSION} to ${NEW_VERSION}"

# ── 1. Node type ────────────────────────────────────────────────────────────
AST=$(command -v asterisk 2>/dev/null || ls /usr/sbin/asterisk /usr/local/sbin/asterisk 2>/dev/null | head -1 || true)
if [ -z "$TYPE" ]; then
  if [ -d /home/irlp/scripts ] || [ -f /home/irlp/custom/environment ]; then
    TYPE=irlp
  elif [ -f /etc/asterisk/rpt.conf ] && [ -n "$AST" ]; then
    TYPE=asl
  else
    die "No AllStarLink or IRLP found. Use --type asl or --type irlp"
  fi
fi
case "$TYPE" in asl|irlp) ;; *) die "--type must be asl or irlp" ;; esac

FLAVOR=""
if [ "$TYPE" = asl ]; then
  if [ -f /usr/local/etc/allstar.env ] || [ -d /usr/local/hamvoip-sbin ]; then FLAVOR=HamVOIP
  elif dpkg -s asl3 >/dev/null 2>&1; then FLAVOR="AllStarLink 3"
  else FLAVOR=AllStarLink; fi
  # The service runs as the same user as Asterisk (asterisk on ASL3, root on HamVOIP)
  RUN_USER=$(ps -o user= -C asterisk 2>/dev/null | head -1 | tr -d ' ' || true)
  [ -n "$RUN_USER" ] || { id asterisk >/dev/null 2>&1 && RUN_USER=asterisk || RUN_USER=root; }
  if [ -z "$NODE" ]; then
    NODE=$(grep -m1 -E '^\[[0-9]{3,7}\]' /etc/asterisk/rpt.conf | sed 's/^\[\([0-9]*\)\].*/\1/' || true)
  fi
  c_ok "$FLAVOR, node ${NODE:-?} (service runs as $RUN_USER)"
else
  FLAVOR=IRLP
  RUN_USER=repeater
  id repeater >/dev/null 2>&1 || die "The IRLP user 'repeater' does not exist"
  if [ -z "$NODE" ]; then
    NODE=$(bash -c '. /home/irlp/custom/environment 2>/dev/null; echo "${STATIONID:-}"' || true)
  fi
  c_ok "IRLP ${NODE:-?} (service runs as $RUN_USER)"
fi
RUN_GROUP=$(id -gn "$RUN_USER")
HAS_IRLP=0; [ -d /home/irlp/scripts ] && id repeater >/dev/null 2>&1 && HAS_IRLP=1
HAS_ASL=0; [ -f /etc/asterisk/rpt.conf ] && [ -n "$AST" ] && HAS_ASL=1
[ "$HAS_IRLP" = 1 ] && [ "$HAS_ASL" = 1 ] && c_ok "This node has both ASL and IRLP: connections can be scheduled on both"

# ── 2. Python and audio tools ───────────────────────────────────────────────
PY=$(command -v python3 || true)
[ -n "$PY" ] || die "python3 is missing"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 5) else 1)' || die "Python 3.5 or newer is required"
c_ok "$("$PY" --version 2>&1)"

if [ "$APT" = 1 ] && command -v apt-get >/dev/null 2>&1; then
  PKGS="ffmpeg espeak-ng"
  [ "$TYPE" = irlp ] && PKGS="$PKGS alsa-utils"
  MISSING=""
  # Look for the command, not the package: asl3-tts ships its own espeak-ng
  # (and libespeak-ng), and the Debian package clashes with it.
  for p in $PKGS; do
    c=$p; [ "$p" = alsa-utils ] && c=aplay
    command -v "$c" >/dev/null 2>&1 || dpkg -s "$p" >/dev/null 2>&1 || MISSING="$MISSING $p"
  done
  if dpkg -s asl3-tts >/dev/null 2>&1; then MISSING=$(echo "$MISSING" | sed 's/ espeak-ng//'); fi
  if [ -n "$MISSING" ]; then
    c_info "Installing:$MISSING (may take a few minutes)"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null 2>&1 || c_warn "apt-get update reported errors; continuing"
    # shellcheck disable=SC2086
    apt-get install -y -qq --no-install-recommends $MISSING >/dev/null 2>&1 \
      || c_warn "Could not install:$MISSING (HAMNA works with what is available)"
  fi
elif [ "$FLAVOR" = HamVOIP ]; then
  c_info "HamVOIP: nothing is installed with pacman; using the system's sox and mpg123"
fi
if command -v ffmpeg >/dev/null 2>&1; then
  c_ok "Audio via ffmpeg (all formats, LUFS leveling)"
elif command -v sox >/dev/null 2>&1; then
  command -v mpg123 >/dev/null 2>&1 && MP3=" and MP3 via mpg123" || MP3=" (no MP3: mpg123 is missing)"
  c_ok "Audio via sox$MP3"
else
  die "Neither ffmpeg nor sox is available to convert audio"
fi

# ── 3. Backup, program and data ─────────────────────────────────────────────
systemctl stop "$SERVICE" 2>/dev/null || true
if ls "$DATA_DIR"/hamna.db >/dev/null 2>&1; then
  BK="$BACKUP_DIR/$(date +%Y%m%d_%H%M%S)${OLD_VERSION:+_v$OLD_VERSION}"
  mkdir -p "$BK"
  cp -a "$DATA_DIR"/hamna.db* "$BK/" 2>/dev/null || true
  [ -f "$DATA_DIR/settings.json" ] && cp -a "$DATA_DIR/settings.json" "$BK/"
  [ -d "$APP_DIR/hamna" ] && cp -a "$APP_DIR/hamna" "$BK/program"
  chmod 700 "$BACKUP_DIR" "$BK"
  c_ok "Backup of data and previous program in $BK"
  # keep only the 5 most recent backups
  ls -1dt "$BACKUP_DIR"/*/ 2>/dev/null | tail -n +6 | xargs -r rm -rf
fi
mkdir -p "$APP_DIR" "$DATA_DIR"
rm -rf "$APP_DIR/hamna"
cp -r "$SRC_DIR/hamna" "$APP_DIR/"
rm -rf "$APP_DIR/bin" && mkdir -p "$APP_DIR/bin"
cp "$SRC_DIR"/bin/hamna-* "$APP_DIR/bin/"
sed -i "1s|.*|#!$PY -I|" "$APP_DIR/bin/hamna-cron"
for f in install.sh update.sh uninstall.sh README.md; do [ -f "$SRC_DIR/$f" ] && cp "$SRC_DIR/$f" "$APP_DIR/"; done
find "$APP_DIR" -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
chown -R root:root "$APP_DIR"
chmod -R a+rX "$APP_DIR"
chmod 755 "$APP_DIR"/*.sh "$APP_DIR"/bin/* 2>/dev/null || true
chmod 755 "$APP_DIR" "$APP_DIR/bin"
chown -R "$RUN_USER:$RUN_GROUP" "$DATA_DIR"
chmod 750 "$DATA_DIR"
[ "$TYPE" = irlp ] && { usermod -aG audio repeater 2>/dev/null || true; }
c_ok "Program in $APP_DIR, data in $DATA_DIR"

run_as() { if [ "$RUN_USER" = root ]; then "$@"; else runuser -u "$RUN_USER" -- "$@"; fi; }
hamna() { (cd "$APP_DIR" && run_as env HAMNA_DATA="$DATA_DIR" PYTHONIOENCODING=utf-8 "$PY" -m hamna "$@"); }

TTS=azure
command -v espeak-ng >/dev/null 2>&1 && TTS=espeak
command -v asl-tts >/dev/null 2>&1 && TTS=piper
hamna --init "backend=$TYPE" "node=$NODE" "tts_engine=$TTS"

# ── 4. Administrator user ───────────────────────────────────────────────────
if [ -n "$PASSWORD" ]; then
  hamna --set-password "$PASSWORD" >/dev/null
  c_ok "User admin ready"
elif hamna --has-password; then
  KEPT_USERS=1
  c_ok "Existing users kept"
elif [ -t 0 ]; then
  while :; do
    printf "  Password for the page's admin user: "; stty -echo; read -r P1; stty echo; echo
    printf "  Repeat it: "; stty -echo; read -r P2; stty echo; echo
    [ "$P1" = "$P2" ] && [ ${#P1} -ge 6 ] && break
    c_warn "They do not match or are shorter than 6 characters"
  done
  hamna --set-password "$P1" >/dev/null
  c_ok "User admin ready"
else
  P1=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 10)
  hamna --set-password "$P1" >/dev/null
  c_warn "User: admin   Generated password: $P1   (change it in Settings > My account)"
fi

if [ "$RUN_USER" = root ]; then RUNPFX=""; else RUNPFX="runuser -u $RUN_USER --"; fi
cat > /usr/local/bin/hamna-web-passwd <<EOF
#!/bin/sh
# Changes the password of a HAMNA Web user and signs out its sessions.
#   hamna-web-passwd                 user admin; asks for the new password
#   hamna-web-passwd USER            that user; asks for the new password
#   hamna-web-passwd USER PASSWORD   without asking (it stays in the shell history!)
#   hamna-web-passwd --create USER   create USER as administrator if missing
CREATE=""
if [ "\${1:-}" = "--create" ]; then CREATE="--create"; shift; fi
if [ "\${1:-}" = "--user" ]; then shift; fi
USER_NAME="\${1:-admin}"; [ \$# -gt 0 ] && shift
cd $APP_DIR || exit 1
if [ \$# -gt 0 ]; then
  exec $RUNPFX env HAMNA_DATA=$DATA_DIR PYTHONIOENCODING=utf-8 $PY -m hamna --set-password "\$1" --user "\$USER_NAME" \$CREATE
fi
exec $RUNPFX env HAMNA_DATA=$DATA_DIR PYTHONIOENCODING=utf-8 $PY -m hamna --set-password --user "\$USER_NAME" \$CREATE
EOF
chmod 755 /usr/local/bin/hamna-web-passwd

# ── 4b. sudo rules for cron and connections ─────────────────────────────────
# Limited to the fixed helpers in /opt/hamna-web/bin (owned by root, not
# writable by the service).
SUDOERS=/etc/sudoers.d/hamna-web
rm -f "$SUDOERS"
if [ "$RUN_USER" != root ] && command -v sudo >/dev/null 2>&1 && [ -d /etc/sudoers.d ]; then
  TMP=$(mktemp)
  echo "# HAMNA Web (created by install.sh; removed by uninstall.sh)" > "$TMP"
  [ "$CRON" = 1 ] && echo "$RUN_USER ALL=(root) NOPASSWD: $APP_DIR/bin/hamna-cron" >> "$TMP"
  [ "$HAS_IRLP" = 1 ] && [ "$RUN_USER" != repeater ] && echo "$RUN_USER ALL=(repeater) NOPASSWD: $APP_DIR/bin/hamna-irlp" >> "$TMP"
  if [ "$HAS_ASL" = 1 ] && [ "$TYPE" = irlp ]; then
    AST_USER=$(ps -o user= -C asterisk 2>/dev/null | head -1 | tr -d ' ' || true)
    [ -n "$AST_USER" ] && [ "$AST_USER" != "$RUN_USER" ] && echo "$RUN_USER ALL=($AST_USER) NOPASSWD: $AST -rx *" >> "$TMP"
  fi
  if [ "$(wc -l < "$TMP")" -gt 1 ]; then
    if visudo -cf "$TMP" >/dev/null 2>&1; then
      install -m 440 -o root -g root "$TMP" "$SUDOERS"
      c_ok "sudo rules for cron/connections in $SUDOERS"
    else
      c_warn "Could not validate the sudo rule; the page will not be able to edit cron"
    fi
  fi
  rm -f "$TMP"
elif [ "$RUN_USER" != root ]; then
  c_warn "No sudo: the page will not be able to see root's cron"
fi

# ── 5. Service ──────────────────────────────────────────────────────────────
AFTER="network-online.target"
[ "$TYPE" = asl ] && systemctl cat asterisk >/dev/null 2>&1 && AFTER="$AFTER asterisk.service"
{
  echo "[Unit]"
  echo "Description=HAMNA Web - amateur radio net automation ($FLAVOR)"
  echo "After=$AFTER"
  echo "Wants=network-online.target"
  echo
  echo "[Service]"
  echo "Type=simple"
  echo "User=$RUN_USER"
  [ "$TYPE" = irlp ] && echo "SupplementaryGroups=audio"
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
systemctl is-active --quiet "$SERVICE" || { journalctl -u "$SERVICE" -n 30 --no-pager; die "The service did not start"; }
c_ok "Service $SERVICE running"

# ── 6. Apache: same port as Allmon/Supermon, at /hamna/ ─────────────────────
WEB_URL=""
WEB_SCHEME="https"
apache_conf() {
  cat <<CONF
# HAMNA Web at http(s)://<node>/hamna/ (same port as Allmon3/AllScan/Supermon).
# HAMNA keeps running internally on 127.0.0.1:$PORT. Created by install.sh.
RedirectMatch ^/hamna\$ /hamna/
<Location "/hamna/">
    ProxyPass "http://127.0.0.1:$PORT/" timeout=300
    ProxyPassReverse "http://127.0.0.1:$PORT/"
    ProxyPassReverseCookiePath "/" "/hamna/"
</Location>
CONF
}
if [ "$APACHE" = 1 ]; then
  if command -v a2enconf >/dev/null 2>&1 && [ -d /etc/apache2/conf-available ]; then
    apache_conf > /etc/apache2/conf-available/hamna-web.conf
    a2enmod -q proxy proxy_http >/dev/null 2>&1 || true
    a2enconf -q hamna-web >/dev/null 2>&1 || true
    if apache2ctl configtest >/dev/null 2>&1; then
      systemctl reload apache2 2>/dev/null || true
      WEB_URL="/hamna/"; c_ok "Published by Apache at /hamna/"
    else
      a2disconf -q hamna-web >/dev/null 2>&1 || true
      c_warn "Apache rejected the configuration; /hamna/ was not published"
    fi
  elif [ -f /etc/httpd/conf/httpd.conf ] && [ -d /etc/httpd/conf/extra ]; then
    # HamVOIP / Arch: httpd.conf + conf/extra
    if grep -qE "^\s*LoadModule proxy_http_module" /etc/httpd/conf/httpd.conf; then
      apache_conf > /etc/httpd/conf/extra/hamna-web.conf
      grep -q "conf/extra/hamna-web.conf" /etc/httpd/conf/httpd.conf || \
        printf "\n# HAMNA Web\nInclude conf/extra/hamna-web.conf\n" >> /etc/httpd/conf/httpd.conf
      if apachectl -t >/dev/null 2>&1; then
        systemctl reload httpd 2>/dev/null || true
        WEB_URL="/hamna/"; WEB_SCHEME="http"; c_ok "Published by Apache (httpd) at /hamna/"
      else
        sed -i '/conf\/extra\/hamna-web.conf/d' /etc/httpd/conf/httpd.conf
        c_warn "httpd rejected the configuration; /hamna/ was not published"
      fi
    else
      c_warn "httpd has no mod_proxy_http loaded; /hamna/ was not published"
    fi
  fi
fi

# ── 7. Firewall ─────────────────────────────────────────────────────────────
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  ZONE=$(firewall-cmd --get-default-zone)
  firewall-cmd -q --zone="$ZONE" --add-port="$PORT"/tcp --permanent && firewall-cmd -q --reload
  c_ok "Port $PORT opened in firewalld (zone $ZONE)"
elif command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow "$PORT"/tcp >/dev/null && c_ok "Port $PORT opened in ufw"
fi

# ── 8. Done ─────────────────────────────────────────────────────────────────
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
[ -n "$IP" ] || IP=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -1)
echo
c_ok "HAMNA Web ${NEW_VERSION} installed"
echo
[ -n "$WEB_URL" ] && echo "   Open in the browser:   ${WEB_SCHEME}://${IP:-NODE-IP}${WEB_URL}"
echo "   Direct address:        http://${IP:-NODE-IP}:$PORT"
echo
if [ "$KEPT_USERS" = 1 ]; then echo "   Sign in with:          your HAMNA users (unchanged)"
else echo "   Sign in with:          user admin"; fi
echo "   Change a password:     hamna-web-passwd USER"
if [ "$(id -u)" = 0 ] && [ -n "${SUDO_USER:-}" ]; then echo "   Update:                sudo $APP_DIR/update.sh"
else echo "   Update:                $APP_DIR/update.sh"; fi
echo "   View the log:          journalctl -u $SERVICE -f"
echo "   Uninstall:             sudo $APP_DIR/uninstall.sh"
echo
