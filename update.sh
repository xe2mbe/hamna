#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  HAMNA Web — updater
#
#  Installs the latest RELEASE (the newest vX.Y.Z tag on GitHub) with its
#  install.sh, which keeps all data, users and settings (and backs up first).
#
#  Usage:   sudo /opt/hamna-web/update.sh [options]
#     or:   curl -sL https://raw.githubusercontent.com/xe2mbe/hamna/main/update.sh | sudo bash
#
#    --version vX.Y.Z     install that release instead of the latest one
#    --branch NAME        install a branch (e.g. main) instead of a release —
#                         only for testing: it may contain unfinished changes
#    --repo OWNER/NAME    GitHub repository (default: xe2mbe/hamna)
#    Any other option is passed to install.sh (e.g. --force, --no-apache).
#    apt packages are not touched on updates (--no-packages is implied).
# ─────────────────────────────────────────────────────────────────────────────
set -eu

REPO="xe2mbe/hamna"
BRANCH=""
WANT=""
PASS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --version) WANT="$2"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0" 2>/dev/null || true; exit 0 ;;
    *) PASS+=("$1"); shift ;;
  esac
done

info() { printf '\033[1;34m[..]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[XX] %s\033[0m\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "Run it as root:  sudo $0"

fetch() {   # fetch URL to stdout
  if command -v curl >/dev/null 2>&1; then curl -fsSL "$1"
  elif command -v wget >/dev/null 2>&1; then wget -qO- "$1"
  else die "Neither curl nor wget is available"; fi
}

INSTALLED=""
[ -f /opt/hamna-web/hamna/__init__.py ] && INSTALLED=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' /opt/hamna-web/hamna/__init__.py)

if [ -n "$BRANCH" ]; then
  REF="refs/heads/$BRANCH"
  info "Installing branch '$BRANCH' (testing only)"
else
  if [ -z "$WANT" ]; then
    # Newest vX.Y.Z tag
    WANT=$(fetch "https://api.github.com/repos/$REPO/tags?per_page=100" | python3 -c '
import json, re, sys
tags = [t["name"] for t in json.load(sys.stdin) if re.match(r"^v\d+\.\d+(\.\d+)?$", t["name"])]
key = lambda v: tuple(int(x) for x in v[1:].split("."))
print(max(tags, key=key) if tags else "")') || die "Could not read the releases from GitHub"
    [ -n "$WANT" ] || die "No releases (vX.Y.Z tags) found in $REPO"
  fi
  case "$WANT" in v*) ;; *) WANT="v$WANT" ;; esac
  REF="refs/tags/$WANT"
  if [ -n "$INSTALLED" ] && [ "v$INSTALLED" = "$WANT" ]; then
    printf '\033[1;32m[ok]\033[0m HAMNA Web %s is already installed (latest release). Re-installing it.\n' "$INSTALLED"
  else
    info "Latest release: $WANT${INSTALLED:+ (installed: v$INSTALLED)}"
  fi
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
URL="https://github.com/$REPO/archive/$REF.tar.gz"
info "Downloading $URL"
fetch "$URL" | tar xz -C "$TMP" || die "Download failed"
SRC=$(ls -d "$TMP"/*/ | head -1)
[ -f "$SRC/install.sh" ] || die "The download does not contain install.sh"
bash "$SRC/install.sh" --no-packages ${PASS[@]+"${PASS[@]}"}
