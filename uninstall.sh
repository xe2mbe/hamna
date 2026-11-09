#!/usr/bin/env bash
# HAMNA Web — uninstaller.   Usage: sudo ./uninstall.sh [--delete-data]
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Run it as root"; exit 1; }

systemctl disable --now hamna-web 2>/dev/null || true
rm -f /etc/systemd/system/hamna-web.service /usr/local/bin/hamna-web-passwd /etc/sudoers.d/hamna-web
systemctl daemon-reload

# Apache /hamna/
if [ -f /etc/apache2/conf-available/hamna-web.conf ]; then
  a2disconf -q hamna-web >/dev/null 2>&1 || true
  rm -f /etc/apache2/conf-available/hamna-web.conf
  systemctl reload apache2 2>/dev/null || true
fi
if [ -f /etc/httpd/conf/extra/hamna-web.conf ]; then
  sed -i '/^# HAMNA Web$/d; /conf\/extra\/hamna-web.conf/d' /etc/httpd/conf/httpd.conf
  rm -f /etc/httpd/conf/extra/hamna-web.conf
  systemctl reload httpd 2>/dev/null || true
fi

rm -rf /opt/hamna-web

case "${1:-}" in
  --delete-data|--borrar-datos)
    rm -rf /var/lib/hamna /var/backups/hamna
    echo "HAMNA Web uninstalled and its data deleted." ;;
  *)
    echo "HAMNA Web uninstalled. Your events and audio are still in /var/lib/hamna"
    echo "(delete them with: rm -rf /var/lib/hamna)" ;;
esac
