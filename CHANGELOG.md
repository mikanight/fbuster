# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).
Fedora Booster — форк [ALT Booster](https://github.com/plafonlinux/altbooster). История изменений ниже отражает только форк.

## [0.0.1-alfa] — 2026-05-07

### Первый альфа-релиз форка

Форк ALT Booster, адаптированный под Fedora Linux (GNOME). Все отличия от оригинала перечислены в README.

#### Добавлено

- **DNF/DNF5** — полная замена apt-get/EPM во всех операциях (установка, удаление, обновление, проверки)
- **Ghostty** — современный GPU-терминал из COPR (`scottames/ghostty`) вместо Ptyxis
- **System76 Scheduler** — установка из COPR (`kylegospo/system76-scheduler`) на отдельной вкладке «Планировщик»
- **Zorkiy** — GNOME расширение для отслеживания фокусного окна и приоритизации CPU
- **Начало** — обновление системы через `dnf upgrade`, проверка Fedora-релиза
- **Консольный лог** — запись всех операций в `~/.config/altbooster/altbooster.log`
- **Ссылка на GitHub** — `mikanight` в диалоге «О приложении»

#### Удалено (относительно ALT Booster)

- EPM, apt-get, `apt-get update` → DNF
- Ptyxis → Ghostty
- zplug (менеджер плагинов ZSH)
- ALT Zero (боковая панель, ссылки, CSS бейдж)
- Sisyphus (ветка ALT Linux)
- ananicy-cpp, LAVD, sched_ext, Intel SCX Meteor
- AMD overdrive (GRUB `amdgpu.ppfeaturemask`)
- Self-update (скачивание и выполнение скриптов с GitHub)
- `--nogpgcheck` (GPG-верификация для COPR)
- Нижняя лог-панель (Gtk.Expander)
- Алиасы ZSH (вкладка Терминал)
- `usermod -aG wheel`

#### Безопасность

- Whitelist допустимых команд в `privileges.py` (`dnf`, `systemctl`, `btrfs`, …)
- Валидация shell-скриптов: запрет `curl | sh`, `chmod 777`, `>/dev/`
- Валидация аргументов `rm`, `install`, `find`, `tar`, `git`, `npm`
- Thread-safe I/O в pkexec-оболочке (`_pkexec_io_lock`)
- `errors="replace"` для UTF-8 — защита от краша на битых байтах кириллицы

#### Рефакторинг

- Импорты упорядочены (PEP 8, ruff без E402)
- Magic numbers → именованные константы
- `VERSION` читается из `pyproject.toml` через `tomllib`
- `BUILTIN_REGISTRY` — ленивая загрузка (decoupling от конкретных табов)
- `_validate_shell_script()` — проверка опасных паттернов в `bash -c`
- `grp.getgrnam("wheel")` вместо `grp.getgrall()` в `amd.py`
- `_FIX_TASK_IDS` — константа для задач в TweaksPage
- Таймаут pkexec-оболочки: 60с → 10с
- Race condition в log writer исправлен
- Хрупкий uninstall в AppRow исправлен (проверка по полям вместо `str(src)`)
- Удалён файл `style.css` — стили встроены в Python
- Удалён мёртвый файл `intel.py`
