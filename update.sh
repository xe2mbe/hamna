#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  HAMNA Web — updater
#
#  Downloads the latest version from GitHub and runs its install.sh, which
#  keeps all data, users and settings (and makes a backup first).
#
#  Usage:   sudo /opt/hamna-web/update.sh [install.sh options]
#     or:   curl -sL https://raw.githubusercontent.com/xe2mbe/hamna/main/update.sh | sudo bash
#
#    --repo OWNER/NAME    GitHub repository (default: xe2mbe/hamna)
#    --branch NAME        branch to install (default: main)
#    Any other option is passed to install.sh (e.g. --force, --no-apache).
#    apt packages are not touched on updates (--no-packages is implied).
# ─────────────────────────────────────────────────────────────────────────────
set -eu

REPO="xe2mbe/hamna"
BRANCH="main"
PASS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0" 2>/dev/null || true; exit 0 ;;
    *) PASS+=("$1"); shift ;;
  esac
done

die() { printf '\033[1;31m[XX] %s\033[0m\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "Run it as root:  sudo $0"

INSTALLED=""
[ -f /opt/hamna-web/hamna/__init__.py ] && INSTALLED=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' /opt/hamna-web/hamna/__init__.py)

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
URL="https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz"
printf '\033[1;34m[..]\033[0m Downloading %s\n' "$URL"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" | tar xz -C "$TMP" || die "Download failed"
elif command -v wget >/dev/null 2>&1; then
  wget -qO- "$URL" | tar xz -C "$TMP" || die "Download failed"
else
  die "Neither curl nor wget is available"
fi
SRC=$(ls -d "$TMP"/*/ | head -1)
[ -f "$SRC/install.sh" ] || die "The download does not contain install.sh"
LATEST=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$SRC/hamna/__init__.py")

if [ -n "$INSTALLED" ] && [ "$INSTALLED" = "$LATEST" ]; then
  printf '\033[1;32m[ok]\033[0m HAMNA Web %s is already the latest version (re-installing anyway)\n' "$INSTALLED"
fi
bash "$SRC/install.sh" --no-packages ${PASS[@]+"${PASS[@]}"}
