<div align="center">

# Fedora Booster

Утилита для тонкой настройки и обслуживания Fedora Linux. Форк [ALT Booster](https://github.com/plafonlinux/altbooster), адаптированный под Fedora Workstation (GNOME). Интерфейс на GTK4/Adwaita.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Fedora%20Linux-blue)](https://fedoraproject.org)
[![GTK](https://img.shields.io/badge/GTK-4.0-green)](https://gtk.org)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-345%20passed-brightgreen)]()


---

## О проекте

**Fedora Booster** — форк [ALT Booster](https://github.com/plafonlinux/altbooster), переработанный для Fedora Linux. Оригинальный проект создан [PLAFON](https://github.com/plafonlinux) для ALT Linux. Данный форк адаптирует пакетный менеджер (apt/EPM → DNF), каталоги приложений, расширения GNOME и системные твики под экосистему Fedora.

- **Пакетный менеджер:** DNF/DNF5 вместо apt-get/EPM
- **Приложения:** Flatpak + DNF + GitHub (без EPM)
- **Расширения GNOME:** каталог из 20 расширений (e.g.o. + GitHub)
- **Системные твики:** адаптированы под Fedora (systemd, journald, fstrim, Btrfs)
- **Безопасность:** все привилегированные операции через pkexec + PolicyKit

## Ключевые возможности

### Установка и настройка
- **Менеджер приложений:** каталог из 50+ приложений (Flatpak, DNF, GitHub)
- **Расширения GNOME:** установка по ID с extensions.gnome.org и из GitHub
- **Умный предпросмотр:** перед установкой показывается список пакетов, размер загрузки
- **Автоисправление ошибок:** при 404 (устаревшие индексы) выполняет `dnf makecache` и повторяет установку
- **Data-Driven UI:** большая часть интерфейса генерируется из JSON-файлов

### Система
- **Начало:** автообновление GNOME Software, TRIM (fstrim.timer), лимиты journald, дробное масштабирование
- **Раскладки клавиатуры:** Alt+Shift, CapsLock, Ctrl+Shift, Win+Space с возможностью отката
- **Nautilus:** настройка сортировки папок, кэш копирования (vm.dirty), Sushi, f3d, иконки Papirus
- **Обслуживание:** очистка DNF/Flatpak, Btrfs scrub/balance, SSD TRIM
- **Твики:** GNOME Shell патчи, приоритеты процессов, sched_ext

### Резервное копирование
- **TimeSync:** бэкапы через BorgBackup
- **Зеркало:** клонирование системы на внешний диск (Btrfs send/receive)
- **Метаданные:** сохранение списка пакетов, Flatpak-приложений, dconf

### AMD / Intel
- **AMD Radeon:** разгон, управление через LACT
- **Intel:** sched_ext планировщик (scx_meteor)

## Требования

- Fedora Linux (GNOME)
- Python 3.11+
- GTK 4.0 + libadwaita
- git

## Установка

### Из PyPI

```bash
pip install fedorabooster
```

### Из GitHub

```bash
git clone https://github.com/mikanight/fbuster.git
cd fbuster
./install.sh
```

### Запуск

```bash
fedorabooster
# или через меню приложений GNOME
```

Флаги: `-s` (Начало), `-a` (Приложения), `-e` (Расширения), `-f` (Твики), `-t` (TimeSync), `-m` (Обслуживание), `--debug`.

### Удаление

```bash
./uninstall.sh
```

## Структура проекта

```
fedorabooster/
├── icons/                     # Иконки (.svg, .png)
├── src/                       # Исходный код
│   ├── altbooster.py          # Точка входа
│   ├── core/                  # Бэкенд: система, пакеты, Borg, Btrfs
│   │   ├── backend.py         # Фасад (реэкспорт API)
│   │   ├── borg.py            # BorgBackup
│   │   ├── btrfs.py           # Btrfs: снапшоты, subvolume
│   │   ├── checks.py          # Проверки состояния системы
│   │   ├── config.py          # Версия, пути, состояние
│   │   ├── gsettings.py       # Обёртки gsettings/dconf
│   │   ├── mirror.py          # Зеркалирование системы
│   │   ├── packages.py        # DNF/Flatpak: установка, предпросмотр
│   │   ├── privileges.py      # pkexec, DNF-блокировки
│   │   ├── sched_ext.py       # sched_ext
│   │   └── tweaks.py          # Системные твики
│   ├── modules/               # JSON-описания для Data-Driven UI
│   ├── tabs/                  # Вкладки приложения
│   │   ├── setup.py           # «Начало»
│   │   ├── apps.py            # «Приложения»
│   │   ├── extensions.py      # «Расширения GNOME»
│   │   ├── flatpak.py         # «Flatpak»
│   │   ├── terminal.py        # «Терминал»
│   │   ├── amd.py             # «AMD Radeon»
│   │   ├── intel.py           # «Intel»
│   │   ├── davinci.py         # «DaVinci Resolve»
│   │   ├── maintenance.py     # «Обслуживание»
│   │   ├── tweaks.py          # «Твики»
│   │   └── timesync/          # «TimeSync» (BorgBackup)
│   └── ui/                    # UI-компоненты
│       ├── window.py          # Главное окно
│       ├── rows.py            # ActionRow/ExpanderRow
│       ├── dynamic_page.py    # Data-Driven движок
│       ├── style.css          # GTK-стили
│       └── ...
├── tests/                     # Тесты (345)
├── install.sh / uninstall.sh  # Скрипты установки/удаления
├── Makefile                   # make install
├── pyproject.toml             # Метаданные, ruff
└── README.md
```

## Отличия от ALT Booster

| Оригинал (ALT Linux) | Форк (Fedora) |
|---|---|
| apt-get / EPM | DNF / DNF5 |
| `apt-get update` | `dnf makecache` |
| `epm -i` / `epm -e` | `dnf install` / `dnf remove` |
| `update-grub` | `grub2-mkconfig` |
| `usermod -aG wheel` | удалено (Fedora включает sudo из коробки) |
| `nautilus-admin-gtk4` | удалено (нет в Fedora) |
| `papirus-remix-icon-theme` | `papirus-icon-theme` |
| `altbooster` (команда) | `fedorabooster` |
| нет проверки is_system_busy | PackageKit + DNF lock |

## Разработка

```bash
# Клонировать
git clone https://github.com/mikanight/fbuster.git
cd fbuster

# Установить в dev-режиме
pip install -e .

# Запустить тесты
pytest tests/ -q

# Линтер
ruff check src/ tests/
```

## Лицензия

[MIT](LICENSE) © 2026 [PLAFON](https://github.com/plafonlinux) (оригинал) · форк [mikanight](https://github.com/mikanight)
