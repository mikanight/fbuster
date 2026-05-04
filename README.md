<div align="center">

# Fedora Booster

Утилита для тонкой настройки и обслуживания Fedora Linux.

Форк [ALT Booster](https://github.com/plafonlinux/altbooster), адаптированный под Fedora Workstation (GNOME). Интерфейс на GTK4/Adwaita.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Fedora%20Linux-blue)](https://fedoraproject.org)
[![GTK](https://img.shields.io/badge/GTK-4.0-green)](https://gtk.org)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-345%20passed-brightgreen)]()

</div>

---

## О проекте

**Fedora Booster** — форк [ALT Booster](https://github.com/plafonlinux/altbooster) от [PLAFON](https://github.com/plafonlinux), адаптированный под Fedora Linux:

- **Пакетный менеджер:** DNF/DNF5 вместо apt-get/EPM
- **Приложения:** каталог 50+ приложений (Flatpak, DNF, GitHub)
- **Расширения GNOME:** каталог из 20 расширений (extensions.gnome.org + GitHub)
- **Системные твики:** адаптированы под Fedora (systemd, journald, fstrim, Btrfs)
- **Безопасность:** привилегированные операции через pkexec + PolicyKit

## Возможности

### Приложения и расширения
- Умный предпросмотр перед установкой (список пакетов, размер загрузки)
- Автоисправление ошибок: при устаревших индексах выполняет `dnf makecache` и повторяет установку
- Data-Driven UI — интерфейс генерируется из JSON-файлов

### Система (вкладка «Начало»)
- Автообновление GNOME Software, TRIM (fstrim.timer), лимиты journald
- Дробное масштабирование, настройка Nautilus, иконки Papirus
- Раскладки клавиатуры: Alt+Shift, CapsLock, Ctrl+Shift, Win+Space с откатом

### Обслуживание и твики
- Очистка кэша DNF/Flatpak, Btrfs scrub/balance, SSD TRIM
- GNOME Shell патчи, планировщик System76 Scheduler

### Резервное копирование (TimeSync)
- Бэкапы через BorgBackup, зеркалирование системы на внешний диск (Btrfs send/receive)
- Сохранение метаданных: список пакетов, Flatpak-приложений, dconf

### AMD / Intel
- AMD Radeon: разгон, управление через LACT
- Intel: планировщик sched_ext (scx_meteor)

## Требования

- Fedora Linux (GNOME)
- Python 3.11+
- GTK 4.0 + libadwaita
- git

## Установка

```bash
# Из PyPI
pip install fedorabooster

# Из GitHub
git clone https://github.com/mikanight/fbuster.git
cd fbuster
./install.sh
```

## Запуск

```bash
fedorabooster                 # основной запуск
fedorabooster -s              # вкладка «Начало»
fedorabooster -a              # вкладка «Приложения»
fedorabooster -e              # вкладка «Расширения»
fedorabooster -m              # вкладка «Обслуживание»
fedorabooster --debug         # режим отладки
```

Удаление: `./uninstall.sh`

## Отличия от ALT Booster

| Оригинал (ALT Linux) | Форк (Fedora) |
|----------------------|---------------|
| apt-get / EPM | DNF / DNF5 |
| `epm -i` / `epm -e` | `dnf install` / `dnf remove` |
| `apt-get update` | `dnf makecache` |
| `update-grub` | `grub2-mkconfig` |
| `usermod -aG wheel` | удалено (Fedora включает sudo по умолчанию) |
| `nautilus-admin-gtk4` | удалено (нет в Fedora) |
| `papirus-remix-icon-theme` | `papirus-icon-theme` |
| `altbooster` (команда) | `fedorabooster` |
| ananicy-cpp, LAVD | System76 Scheduler |

## Разработка

```bash
git clone https://github.com/mikanight/fbuster.git
cd fbuster
pip install -e .

pytest tests/ -q              # тесты (345)
ruff check src/ tests/        # линтер
```

## Структура

```
src/
├── altbooster.py          # Точка входа
├── core/                  # Бэкенд (система, DNF, Borg, Btrfs, pkexec)
├── modules/               # JSON-описания для Data-Driven UI
├── tabs/                  # Вкладки (setup, apps, extensions, flatpak, terminal, amd, davinci, maintenance, tweaks, timesync)
└── ui/                    # UI-компоненты (window, rows, dynamic_page, style.css)
```

## Лицензия

[MIT](LICENSE) © 2026 [PLAFON](https://github.com/plafonlinux) (оригинал) · форк [mikanight](https://github.com/mikanight)
