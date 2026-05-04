#!/bin/bash
# Fedora Booster — Install Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/usr/local/share/fedorabooster"
ICON_DIR="/usr/local/share/icons/hicolor/scalable/apps"
DESKTOP_DIR="/usr/local/share/applications"
BIN="/usr/local/bin/fedorabooster"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

if [[ $EUID -ne 0 ]]; then
    DE="${XDG_CURRENT_DESKTOP:-${DESKTOP_SESSION:-unknown}}"
    if [[ ! "$DE" =~ [Gg][Nn][Oo][Mm][Ee] ]]; then
        echo -e "${YELLOW}⚠  Fedora Booster разработан для GNOME.${NC}"
        echo -e "   Обнаружено окружение: ${BOLD}${DE}${NC}"
        echo -e "   Приложение использует GTK4 + libadwaita и не тестировалось на других DE."
        echo ""
        read -r -p "   Продолжить установку? [y/N] " _confirm
        [[ "$_confirm" =~ ^[Yy]$ ]] || exit 0
        echo ""
    fi
    echo -e "${YELLOW}🔒 Требуются права root...${NC}"
    if command -v pkexec >/dev/null 2>&1; then
        pkexec "$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")" "$@"
        exit $?
    else
        sudo "$0" "$@"
        exit $?
    fi
fi

echo -e "${BOLD}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║    Fedora Booster  Installer         ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

step() { echo -ne "  ${YELLOW}▶${NC} $1... "; }
ok()   { echo -e "${GREEN}✔${NC}"; }
fail() { echo -e "${RED}✘ $1${NC}"; exit 1; }

# Установка зависимостей
step "Проверка зависимостей"
MISSING=()
python3 -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" 2>/dev/null \
    || MISSING+=("python3-gobject" "gtk4")
python3 -c "import gi; gi.require_version('Adw','1'); from gi.repository import Adw" 2>/dev/null \
    || MISSING+=("libadwaita")
if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo ""
    echo -e "  ${YELLOW}Устанавливаю зависимости: ${MISSING[*]}${NC}"
    dnf install -y "${MISSING[@]}" || fail "Не удалось установить зависимости"
fi
ok

# Файлы приложения
step "Копирование файлов"
install -d "$APP_DIR"
cp -r "$SCRIPT_DIR/src/"* "$APP_DIR/"
chmod +x "$APP_DIR/altbooster.py"
ok

# Иконки
step "Установка иконок"
install -d "$ICON_DIR"
install -m 644 "$SCRIPT_DIR/icons/fedorabooster.svg" "$ICON_DIR/fedorabooster.svg"
install -d "/usr/local/share/icons/hicolor/scalable/apps"
for _svg in "$SCRIPT_DIR/icons/hicolor/scalable/apps/"*.svg; do
    install -m 644 "$_svg" "/usr/local/share/icons/hicolor/scalable/apps/"
done
install -d "/usr/local/share/icons/hicolor/scalable/devices"
for _svg in "$SCRIPT_DIR/icons/hicolor/scalable/devices/"*.svg; do
    install -m 644 "$_svg" "/usr/local/share/icons/hicolor/scalable/devices/"
done
gtk-update-icon-cache /usr/local/share/icons/hicolor 2>/dev/null || true
ok

# .desktop
step "Создание ярлыка"
install -d "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/fedorabooster.desktop" << DESKTOP
[Desktop Entry]
Name=Fedora Booster
GenericName=System Maintenance
Comment=Утилита обслуживания системы Fedora Linux
Exec=$BIN
Icon=fedorabooster
Terminal=false
Type=Application
Categories=System;Settings;
Keywords=system;maintenance;clean;btrfs;trim;dnf;flatpak;
StartupNotify=true
StartupWMClass=org.fedorabooster.app
DESKTOP
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
ok

# Справка (Yelp / Mallard)
step "Установка справки"
install -d "/usr/local/share/help/C/fedorabooster"
cp -r "$SCRIPT_DIR/help/C/"* "/usr/local/share/help/C/fedorabooster/"
ok

# Команда в PATH
step "Создание команды fedorabooster"
cat > "$BIN" << 'BINEOF'
#!/bin/bash
exec python3 /usr/local/share/fedorabooster/altbooster.py "$@"
BINEOF
chmod +x "$BIN"
ok

echo ""
echo -e "  ${GREEN}${BOLD}✅ Fedora Booster успешно установлен!${NC}"
echo ""
echo -e "  Запуск: ${BOLD}fedorabooster${NC}  или через меню приложений GNOME"
echo ""
