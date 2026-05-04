#!/bin/bash
# Fedora Booster — Uninstall Script
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

if [[ $EUID -ne 0 ]]; then
    echo "🔒 Требуются права root..."
    sudo "$0" "$@"
    exit $?
fi

echo "Удаление Fedora Booster..."
rm -rf "/usr/local/share/fedorabooster"
rm -f "/usr/local/share/icons/hicolor/scalable/apps/fedorabooster.svg"
rm -f "/usr/local/share/applications/fedorabooster.desktop"
rm -f "/usr/local/bin/fedorabooster"
gtk-update-icon-cache /usr/local/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/local/share/applications 2>/dev/null || true

echo "✔ Fedora Booster успешно удален."
