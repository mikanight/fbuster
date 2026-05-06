# Участие в разработке

Спасибо за интерес к Fedora Booster! Этот документ поможет понять архитектуру приложения и стандарты кода.

## Философия и архитектура

Fedora Booster — форк [ALT Booster](https://github.com/plafonlinux/altbooster), адаптированный под Fedora Linux. Ключевые принципы:

1. **Безопасность:** Все привилегированные операции используют `pkexec` + PolicyKit. Выполняемые команды проходят валидацию через whitelist в `src/core/privileges.py`. Shell-скрипты (`bash -c`) проверяются на опасные паттерны (`curl | sh`, `chmod 777`, `>/dev/`). `--nogpgcheck` не используется.

2. **Отзывчивый интерфейс:** Все длительные задачи (сеть, установка пакетов, проверки) выполняются в `threading.Thread`, результаты передаются в GTK через `GLib.idle_add`.

3. **Разделение логики:**
   - **Вкладки (`src/tabs/`):** Каждая вкладка — отдельный модуль.
   - **UI-компоненты (`src/ui/`):** Переиспользуемые виджеты, строки, диалоги, поиск.
   - **Бэкенд (`src/core/`):** Системная логика, DNF, Borg, Btrfs, проверки. Фасад `src/core/backend.py` — единая точка входа.

4. **Data-Driven UI:** Вкладки «Обслуживание» и «AMD» генерируются из JSON-файлов в `src/modules/`. Движок в `src/ui/dynamic_page.py`. Каталог приложений — `src/modules/apps.json`.

## Структура проекта

```
fbuster/
├── icons/                     # Иконки (.svg)
├── src/                       # Исходный код
│   ├── altbooster.py          # Точка входа
│   ├── core/                  # Бэкенд
│   │   ├── backend.py         # Фасад для вкладок
│   │   ├── checks.py          # Проверки состояния системы
│   │   ├── config.py          # Конфигурация и константы
│   │   ├── privileges.py      # Безопасный pkexec (whitelist, валидация)
│   │   ├── packages.py        # Работа с RPM/Flatpak
│   │   ├── borg.py            # Логика BorgBackup
│   │   ├── btrfs.py           # Логика Btrfs
│   │   ├── mirror.py          # Зеркалирование системы
│   │   ├── gsettings.py       # Обёртки gsettings/dconf
│   │   └── tweaks.py          # Системные твики
│   ├── modules/               # JSON-описания для Data-Driven UI
│   │   ├── apps.json          # Каталог приложений
│   │   ├── maintenance.json   # Задачи обслуживания
│   │   ├── terminal.json      # Терминал (Data-Driven)
│   │   └── amd.json           # AMD Radeon (Data-Driven)
│   ├── tabs/                  # Вкладки
│   │   ├── setup.py           # Начало
│   │   ├── apps.py            # Приложения
│   │   ├── extensions.py      # Расширения GNOME
│   │   ├── flatpak.py         # Flatpak
│   │   ├── terminal.py        # Терминал (Ghostty, ZSH, Fastfetch)
│   │   ├── amd.py             # AMD Radeon
│   │   ├── davinci.py         # DaVinci Resolve
│   │   ├── maintenance.py     # Обслуживание
│   │   ├── tweaks.py          # Твики (общие фиксы)
│   │   ├── scheduler.py       # Планировщик (System76 + Zorkiy)
│   │   └── timesync/          # TimeSync (BorgBackup)
│   └── ui/                    # UI-компоненты
│       ├── window.py          # Главное окно и боковая панель
│       ├── dynamic_page.py    # Data-Driven UI движок
│       ├── global_search.py   # Глобальный поиск (Ctrl+K)
│       ├── rows.py            # SettingRow, AppRow, TaskRow
│       ├── widgets.py         # Фабрики GTK-виджетов
│       └── common.py          # Загрузка JSON-модулей
├── install.sh                 # Скрипт установки
├── uninstall.sh               # Скрипт удаления
└── pyproject.toml             # Метаданные проекта (PEP 621)
```

## Как добавить приложение в каталог

Каталог приложений: `src/modules/apps.json`. Найдите группу (например, `"id": "browsers"`) и добавьте объект в `items`.

**Структура приложения:**
- `id` — уникальный идентификатор (`snake_case`)
- `label` — название
- `desc` — описание
- `sources` — список источников установки

**Структура источника:**
- `label` — текст бейджа (например, "DNF", "Flathub", "COPR")
- `cmd` — команда установки (список аргументов)
- `check` — проверка: `["rpm", "pkgname"]`, `["flatpak", "app.id"]`, `["which", "binary"]`

**Примеры:**
```json
// RPM-пакет
{
  "id": "firefox",
  "label": "Firefox",
  "desc": "Веб-браузер",
  "sources": [
    {
      "label": "DNF",
      "cmd": ["dnf", "install", "-y", "firefox"],
      "check": ["rpm", "firefox"]
    }
  ]
}

// Flatpak
{
  "id": "telegram",
  "label": "Telegram",
  "desc": "Мессенджер",
  "sources": [
    {
      "label": "Flathub",
      "cmd": ["flatpak", "install", "-y", "flathub", "org.telegram.desktop"],
      "check": ["flatpak", "org.telegram.desktop"]
    }
  ]
}

// GitHub (сборка из исходников)
{
  "id": "monitor_control",
  "label": "Monitor Control",
  "desc": "Управление яркостью внешних мониторов",
  "sources": [
    {
      "label": "GitHub",
      "cmd": [...],
      "check": ["which", "monitor-control"]
    }
  ]
}
```

## Как добавить задачу обслуживания

Задачи: `src/modules/maintenance.json`. Добавьте объект в массив `tasks`.

**Структура задачи:**
- `id` — уникальный идентификатор
- `icon` — иконка Adwaita (например, `user-trash-symbolic`)
- `label` — название
- `desc` — описание
- `cmd` — команда (выполняется через `pkexec`)
- `type` (опционально) — `"user"` для выполнения без `sudo`
- `check` (опционально) — проверка выполнения

## Стиль кода

```bash
ruff check src/ tests/        # линтер
pytest tests/ -q              # тесты (332)
```

- Длина строки — 100 символов
- `import` в начале файла (PEP 8)
- `bare except` запрещён — указывайте тип (`except OSError:`)
- Комментарии не нужны — код должен быть самодокументируемым
- Magic numbers — в именованные константы

## Pull Request

1. Форк репозитория
2. Ветка: `git checkout -b feat/my-feature`
3. Проверка: `ruff check src/ && pytest tests/ -q`
4. Pull Request с описанием **что** и **зачем** изменено
