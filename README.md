<div align="center">

# Fedora Booster

Утилита для тонкой настройки и обслуживания Fedora Linux.

Форк [ALT Booster](https://github.com/plafonlinux/altbooster), адаптированный под Fedora Workstation (GNOME). Интерфейс на GTK4/Libadwaita.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Fedora%20Linux-blue)](https://fedoraproject.org)
[![GTK](https://img.shields.io/badge/GTK-4.0-green)](https://gtk.org)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-332%20passed-brightgreen)]()

</div>

---

## О проекте

**Fedora Booster** — форк [ALT Booster](https://github.com/plafonlinux/altbooster) от [PLAFON](https://github.com/plafonlinux), адаптированный под Fedora Linux. Приложение предоставляет единый интерфейс для:

- Установки и удаления приложений из DNF, Flatpak и GitHub
- Управления расширениями GNOME Shell
- Системных твиков (journald, fstrim, Btrfs, раскладки клавиатуры)
- Настройки терминала (Ghostty, ZSH, Fastfetch)
- Обслуживания системы (очистка кэша, TRIM, Btrfs scrub)
- Резервного копирования через BorgBackup (TimeSync)
- Установки System76 Scheduler с расширением Zorkiy

Интерфейс — 10 вкладок в боковой панели, глобальный поиск (Ctrl+K), обработка ошибок DNF с автоматическим `dnf makecache`.

## Возможности

### Приложения и расширения
- Каталог 50+ приложений (Flatpak, DNF, GitHub, COPR)
- Умный предпросмотр перед установкой (список пакетов, размер загрузки)
- Автоисправление ошибок: при устаревших индексах выполняет `dnf makecache` и повторяет установку
- Data-Driven UI — интерфейс генерируется из JSON-файлов
- 20+ расширений GNOME (extensions.gnome.org + GitHub)

### Система (вкладка «Начало»)
- Обновление системы (`dnf upgrade`)
- Автообновление GNOME Software, TRIM (fstrim.timer), лимиты journald
- Дробное масштабирование, настройка Nautilus, иконки Papirus
- Раскладки клавиатуры: Alt+Shift, CapsLock, Ctrl+Shift, Win+Space

### Терминал
- Установка Ghostty из COPR (`scottames/ghostty`)
- Настройка ZSH + Fastfetch + Fira Code
- Горячие клавиши (Ctrl+Alt+T, Super+Enter)

### AMD Radeon
- Разгон и андервольтинг
- LACT: установка, добавление в wheel, импорт конфига

### DaVinci Resolve
- Установка пакетов (ROCm, OpenCL, Fairlight, AAC)
- Автоматическая настройка `vm.max_map_count` и OpenCL

### Обслуживание
- Очистка кэша DNF/Flatpak/журналов/эскизов
- Btrfs scrub/balance, SSD TRIM
- Оптимизация виртуальной памяти, лимиты journald

### Твики
- Исправление конфликта GDM с USB-устройствами
- Исправление GSConnect (KDE Connect для GNOME)
- Отключение Tracker Miner (индексация файлов)

### Планировщик
- Установка **System76 Scheduler** из COPR (`kylegospo/system76-scheduler`)
- Включение/отключение systemd-службы
- Установка расширения **Zorkiy** — отслеживание фокусного окна для приоритизации CPU

### Резервное копирование (TimeSync)
- Полные и инкрементальные бэкапы через BorgBackup
- Зеркалирование системы на внешний диск (Btrfs send/receive)
- Сохранение метаданных: список RPM-пакетов, Flatpak-приложений, dconf
- Планировщик через systemd-таймеры

## Безопасность

- Привилегированные операции — через `pkexec` + PolicyKit с валидацией команд
- Whitelist допустимых команд (`dnf`, `systemctl`, `btrfs`, `rsync`, …)
- Валидация shell-скриптов (запрет `curl | sh`, `chmod 777`, `>/dev/`)
- Без `--nogpgcheck` — все COPR-пакеты проверяются через GPG
- Удалён механизм self-update (скачивание и выполнение скриптов с GitHub)

## Требования

- Fedora Linux (GNOME)
- Python 3.11+
- GTK 4.0 + libadwaita
- git

## Установка

```bash
git clone https://github.com/mikanight/fbuster.git
cd fbuster
sudo ./install.sh
```

Скоро соберу пакет.

## Запуск

```bash
fedorabooster                 # основной запуск
fedorabooster -s              # вкладка «Начало»
fedorabooster -a              # вкладка «Приложения»
fedorabooster -e              # вкладка «Расширения»
fedorabooster -m              # вкладка «Обслуживание»
fedorabooster --debug         # режим отладки (G_MESSAGES_DEBUG=all + exception hook)
```

## Отличия от ALT Booster

| Оригинал (ALT Linux) | Форк (Fedora) |
|----------------------|---------------|
| apt-get / EPM | DNF / DNF5 |
| `epm -i` / `epm -e` | `dnf install` / `dnf remove` |
| `apt-get update` | `dnf makecache` |
| `update-grub` | `grub2-mkconfig` |
| `usermod -aG wheel` | удалено |
| `nautilus-admin-gtk4` | удалено |
| `papirus-remix-icon-theme` | `papirus-icon-theme` |
| `altbooster` (команда) | `fedorabooster` |
| ananicy-cpp, LAVD, sched_ext | System76 Scheduler (COPR) |
| Ptyxis | Ghostty (COPR) |
| zplug, ALT Zero, Sisyphus | удалено |
| Нижняя лог-панель | удалено |
| Self-update через GitHub | удалено |
| Intel SCX Meteor | удалено |

## Разработка

```bash
git clone https://github.com/mikanight/fbuster.git
cd fbuster
pip install -e .

pytest tests/ -q              # тесты (332)
ruff check src/ tests/        # линтер
```

## Структура

```
src/
├── altbooster.py          # Точка входа
├── core/                  # Бэкенд (privileges, backend, checks, config, borg, mirror, packages)
├── modules/               # JSON-описания для Data-Driven UI
├── tabs/                  # Вкладки (setup, apps, extensions, flatpak, terminal, amd, davinci, maintenance, tweaks, scheduler, timesync)
└── ui/                    # UI-компоненты (window, rows, dynamic_page, global_search, widgets)
```

## Лицензия

[MIT](LICENSE) © 2026 [PLAFON](https://github.com/plafonlinux) (оригинал) · форк [mikanight](https://github.com/mikanight)
