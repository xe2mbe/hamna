#!/usr/bin/env bash
# HAMNA Web — desinstalador.  Uso: sudo ./uninstall.sh [--borrar-datos]
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecútalo con sudo"; exit 1; }

systemctl disable --now hamna-web 2>/dev/null || true
rm -f /etc/systemd/system/hamna-web.service /usr/local/bin/hamna-web-passwd
systemctl daemon-reload
rm -rf /opt/hamna-web

if [ "${1:-}" = "--borrar-datos" ]; then
  rm -rf /var/lib/hamna
  echo "HAMNA Web desinstalado y datos borrados."
else
  echo "HAMNA Web desinstalado. Tus eventos y audios siguen en /var/lib/hamna"
  echo "(bórralos con: sudo rm -rf /var/lib/hamna)"
fi
