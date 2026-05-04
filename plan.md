# План миграции ALT Booster → Fedora Booster

## Общая информация

**Исходный проект**: ALT Booster v5.6.9 — GTK4/Adwaita-утилита настройки ALT Linux  
**Цель**: Fedora Booster — порт под Fedora Linux (~41+) с заменой всех ALT-специфичных механизмов на dnf/RPM Fusion/Fedora-эквиваленты  
**Объём**: ~22 000 строк Python, ~47 файлов, затрагивается ~30+ файлов  

---

## Фаза 0: Подготовка

### 0.1. Создание ветки и настройка окружения
- Создать ветку `fedora-port`
- Настроить ruff с текущими параметрами из `pyproject.toml`
- Убедиться, что ruff проходит на исходном коде (baseline)

### 0.2. Инвентаризация
- Просмотреть все точки входа apt-get/epm (используя grep)
- Составить полную карту замены названий пакетов ALT → Fedora

---

## Фаза 1: Пакетный менеджер и привилегии (core/)

*Самый критичный слой — замена apt-get/epm на dnf во всём бэкенде.*

### 1.1 `core/privileges.py`
| Действие | Строки | Описание |
|---|---|---|
| Удалить `_wrap_epm_auto_install()` | 180–191 | Функция автоустановки eepm — не нужна на Fedora |
| Удалить `run_epm()` | 290–293 | Становится алиасом на `run_privileged` |
| Удалить `run_epm_sync()` | 276–288 | Заменить на `run_privileged_sync` |
| Заменить `apt-get install -y eepm` | 188 | Удалить упоминание eepm |
| Обновить `_is_apt_locked()` | 121–127 | Заменить пути APT-локов на DNF: `dnf.pid`, `dnf/lock` |
| Обновить `_wait_for_apt_lock()` | 129–145 | Переименовать в `_wait_for_dnf_lock`, обновить текст |
| Добавить `run_dnf()` | Новый | Обёртка для `dnf install/remove/update` |
| Добавить `run_dnf_sync()` | Новый | Синхронная версия |

### 1.2 `core/packages.py`
| Действие | Строки | Описание |
|---|---|---|
| `_detect_source_type()` | 36–45 | Добавить `"dnf"` как тип источника |
| `_parse_apt_simulate_output()` | 48–128 | Переименовать в `_parse_dnf_output()`, адаптировать парсинг вывода dnf |
| `get_install_preview()` | 228–285 | Заменить `apt-get -s dist-upgrade` / `apt-get -s install` на `dnf distro-sync --setopt=tsflags=test` / `dnf install --assumeno` |
| Удалить `is_dist_upgrade` | 243–247 | DNF использует `dnf upgrade` / `dnf distro-sync` |
| `dry_cmd` формирование | 250–256 | Заменить на dnf-эквиваленты |
| Сохранить логику Flatpak | — | Без изменений (Flatpak одинаков) |

### 1.3 `core/checks.py`
| Действие | Строки | Описание |
|---|---|---|
| Удалить `is_epm_installed()` | 240–244 | EPM не существует на Fedora |
| `is_sudo_enabled()` | 98–103 | Заменить `control sudowheel` → проверка `groups` / `sudo -l` |
| `is_system_busy()` | 129–138 | Обновить пути APT-локов → DNF-локи |
| `_eval_check_pair()` | 72–95 | Добавить `"dnf"` как вид проверки (через `rpm -q`) |
| `check_app_installed()` | 175–183 | Оставить как есть (использует rpm/flatpak/which) |

### 1.4 `core/config.py`
| Действие | Строки | Описание |
|---|---|---|
| `APT_LOCK_FILES` | 39–43 | Заменить на `DNF_LOCK_FILES = ["/var/run/dnf.pid"]` |
| `VERSION` | 16 | Оставить для tracking'а |

### 1.5 `core/backend.py`
| Действие | Строки | Описание |
|---|---|---|
| Удалить импорт `run_epm`, `run_epm_sync` | 11–12 | Заменить на алиасы `run_dnf` |
| Удалить `is_epm_installed` | 30 | Не нужен |
| Добавить импорт `run_dnf`, `run_dnf_sync` | Новый | Из `privileges.py` |

### 1.6 `core/sched_ext.py`
| Действие | Строки | Описание |
|---|---|---|
| `KERNEL_IMAGE_SCHED_EXT` | 11 | Заменить `"kernel-image-6.18"` → `"kernel"` (Fedora использует `kernel`) |
| Убрать упоминание ALT в комментарии | 10–11 | |

### 1.7 `core/mirror.py`
| Действие | Строки | Описание |
|---|---|---|
| `update-grub` | 412, 504, 642 | Заменить на `grub2-mkconfig -o /boot/grub2/grub.cfg` |

---

## Фаза 2: Репозитории и идентичность дистрибутива

### 2.1 `core/checks.py`
| Действие | Строки | Описание |
|---|---|---|
| `is_sisyphus()` — нет такой функции здесь | — | Уже удалена в фазе 1 |

### 2.2 `tabs/setup.py` (1199 строк — самая большая вкладка)
| Действие | Строки | Описание |
|---|---|---|
| Удалить `_SOURCES_DIR` | 22 | `/etc/apt/sources.list.d` → удалить (Fedora использует `/etc/yum.repos.d/`) |
| Удалить `_MIRRORS` | 23–28 | ALT-зеркала не нужны |
| Удалить `_detect_active_mirror()` | 43–55 | Парсинг `.list` файлов |
| Удалить `_build_mirror_switch_cmd()` | 57–65 | |
| `_is_sisyphus()` | 81–90 | Заменить `/etc/altlinux-release` → `/etc/fedora-release` |
| Удалить `_on_epm()` | 350–413 | Вся логика установки/обновления EPM |
| Удалить `_on_install_epm()` | 476–492 | |
| Удалить `_on_remove_epm()` | 484–491 | |
| `_build_system_group()` | — | Удалить EPM-related SettingRow'ы (установка EPM, обновление через EPM) |
| Заменить `apt-get` на `dnf` | Разбросано | Заменить команды установки пакетов (nautilus-admin, sushi, f3d, etc.) |
| Удалить `apt-get dedup` | 727–728 | Нет аналога в Fedora |
| Удалить `apt-repo add task` | 774–778 | ALT-specific task-based package install |
| `_is_newer()` | 93–100 | Оставить (сравнение версий универсально) |
| Заменить `apt-get update` | 454 | → `dnf makecache` |
| Заменить `apt-get dist-upgrade` | 442 | → `dnf distro-sync` или `dnf upgrade` |
| `_on_sudo_enable()` | 857 | Заменить `control sudowheel enabled` → `usermod -aG wheel $USER` |
| `_on_sudo_disable()` | 877 | Заменить `control sudowheel disabled` → `gpasswd -d $USER wheel` |
| `is_sisyphus` check для f3d | 551–572 | Заменить на проверку доступности в Fedora-репах |
| Сообщение `"✔  ALT Linux обновлён!\n"` | 401 | → `"✔  Fedora обновлена!\n"` |

### 2.3 `tabs/tweaks.py` (891 строка — удаление ~300 строк Sisyphus)
| Действие | Строки | Описание |
|---|---|---|
| Удалить `_is_sisyphus()` | 103–112 | |
| Удалить `_detect_branch()` | 115–131 | |
| Удалить `_build_platform_sisyphus_intro()` | 238–271 | Платформа + Sisyphus — не нужны |
| Удалить `_build_sisyphus_group()` | 346–541 | ~200 строк миграции p11→Sisyphus |
| Удалить `_on_check_clicked()` | 421–427 | |
| Удалить `_do_check()` | 429–472 | |
| Удалить `_check_done_error()` | 474–480 | |
| Удалить `_check_done_ok()` | 482–492 | |
| Удалить `_on_revert_clicked()` | 494–517 | |
| Удалить `_on_upgrade_clicked()` | 519–541 | |
| Удалить `_make_branch_badge_label()` | 327–344 | |
| Заменить CSS `.ab-tweak-sisyphus-badge` | 35–43 | Удалить или переименовать |
| Заменить CSS `.ab-tweak-branch-badge-*` | 52–70 | Удалить |
| `_add_info_row()` — убрать `sisyphus_only_badge` | 288–316 | Заменить на Fedora repo availability check |
| `_build_scx_ui()` | 543–587 | Убрать `sisyphus_only_badge`, заменить текст |
| `_enable_lavd()` — `apt-get install -y scx-scheds` | 624 | → `dnf install -y scx-scheds` |
| `_build_ananicy_group()` | 704–761 | Заменить `epm install` → `dnf install`, убрать Sisyphus-гейтинг |
| `_install_ananicy()` — `epm install -y` | 782 | → `dnf install -y` |
| `_uninstall_ananicy()` — `epm remove -y` | 817 | → `dnf remove -y` |

### 2.4 `tabs/apps.py` (977 строк)
| Действие | Строки | Описание |
|---|---|---|
| Заменить `Gtk.StringList.new(["p11", "Sisyphus", "epm play", "Flathub"])` | 63 | → `Gtk.StringList.new(["fc41", "epm play", "Flathub", "rawhide"])` |
| `branch_map` | 165–166 | Заменить p11/Sisyphus → fc41/rawhide |
| `all_branches` | 219 | То же |
| `label_map` | 311 | То же |
| Заменить `rdb.altlinux.org` API URL | 177 | → Fedora Packages API: `https://packages.fedoraproject.org/api/` или `dnf search` |
| Заменить user-agent | 178 | `"ALTBooster/1.0"` → `"FedoraBooster/1.0"` |

### 2.5 JSON-файлы модулей
| Файл | Действие |
|---|---|
| `src/modules/maintenance.json` | Заменить `["apt-get", "clean"]` на `["dnf", "clean", "all"]` |
| `src/modules/terminal.json` | Заменить `apt-get` → `dnf`, `epm` → `dnf`, обновить названия пакетов |
| `src/modules/amd.json` | Заменить `["epm", "-i", "lact"]` на `["dnf", "install", "-y", "lact"]`, заменить `update-grub` на `grub2-mkconfig` |
| `src/modules/apps.json` | Заменить все `epm`/`apt-get` → `dnf`, проверить названия пакетов |

### 2.6 `tabs/flatpak.py` (773 строки)
| Действие | Строки | Описание |
|---|---|---|
| `apt-get install -y flatpak-repo-flathub` | 427, 685, 719 | Заменить на `flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo` |
| `apt-get install -y flatpak` | 436, 690 | → `dnf install -y flatpak` |
| `apt-get remove -y flatpak flatpak-repo-flathub` | 719 | → `dnf remove -y flatpak` (flatpak-repo-flathub нет отдельным пакетом) |

### 2.7 `tabs/terminal.py` (875 строк) и `tabs/terminal_actions.py`
| Действие | Описание |
|---|---|
| Все `apt-get` | → `dnf` |
| Все `epm` / `epmi` | → `dnf` |
| Удалить `alias ep`, `alias epm-help`, `alias eph`, `alias find="epmqp"`, `alias poisk="epms"` | ALT-only алиасы |
| `alias up="epm update && epm full-upgrade && flatpak update"` | → `alias up="sudo dnf upgrade -y && flatpak update -y"` |
| `sudo remove-old-kernels -a` | → `sudo dnf remove $(rpm -qa kernel-core\* \| sort -V \| head -n -2)` |
| `update-grub` алиасы | → `grub2-mkconfig -o /boot/grub2/grub.cfg` |
| `[p11]` в fastfetch config | → `[fc{version}]` |

---

## Фаза 3: Названия пакетов

### 3.1 Полная карта замены

| ALT Linux | Fedora | Где используется |
|---|---|---|
| `eepm` | НЕТ (удалить) | privileges.py, setup.py, checks.py |
| `epmgpi` | НЕТ (удалить) | setup.py |
| `eepm-play-gui` | НЕТ (удалить) | setup.py |
| `apt-repo` | НЕТ (удалить) | setup.py |
| `python3-module-pygobject3` | `python3-gobject` | install.sh |
| `libgtk4-gir` | `gtk4` | install.sh |
| `libadwaita-gir` | `libadwaita` | install.sh |
| `python3-module-pip` | `python3-pip` | apps.json |
| `rocm-opencl-runtime` | `rocm-opencl` | davinci.py (стр.30) |
| `hip-runtime-amd` | `rocm-hip` | davinci.py (стр.30) |
| `libGLU` | `mesa-libGLU` (или `libglu`) | davinci.py (стр.30) |
| `ffmpeg` | `ffmpeg-free` (или `ffmpeg` из RPM Fusion) | davinci.py (стр.30) |
| `alsa-plugins-pulse` | `alsa-plugins-pulseaudio` | davinci.py (стр.41), checks.py |
| `flatpak-repo-flathub` | НЕТ (flatpak remote-add) | flatpak.py |
| `fonts-ttf-fira-code-nerd` | `fira-code-fonts` | terminal.json, terminal.py |
| `nautilus-admin-gtk4` | Проверить доступность (`nautilus-admin`) | setup.py |
| `kernel-image-6.18` | `kernel` | sched_ext.py |
| `scx-scheds` | Проверить в репах Fedora (`scx-scheds`?) | tweaks.py |
| `ananicy-cpp` | Проверить в репах Fedora | tweaks.py |
| `rust`, `rust-cargo` | `rust`, `cargo` | system76_scheduler.py, intel.py |
| `pipewire-libs-devel` | `pipewire-devel` | system76_scheduler.py |
| `bcc-tools` | `bcc` | system76_scheduler.py |
| `clang-devel` | `clang-devel` (то же?) | system76_scheduler.py |
| `btrfs-progs` | `btrfs-progs` (то же) | maintenance.json |
| `borg` | `borgbackup` | timesync/page.py |

### 3.2 Обновляемые файлы
- `install.sh` — строки 49–52 (зависимости Python/GTK/Adwaita)
- `src/tabs/davinci.py` — строки 29–41 (пакеты для DaVinci Resolve)
- `src/tabs/flatpak.py` — строки 427, 436, 685, 690, 719
- `src/tabs/terminal.py` — эпизодически (названия пакетов)
- `src/tabs/system76_scheduler.py` — строки 195–208
- `src/tabs/intel.py` — строка 204
- `src/modules/terminal.json` — строка 129
- `src/modules/apps.json` — эпизодически (названия пакетов в check/cmd)

---

## Фаза 4: Системные команды и пути

### 4.1 `update-grub` → `grub2-mkconfig`
| Файл | Строки | Замена |
|---|---|---|
| `src/core/mirror.py` | 412, 504, 642 | `chroot ... update-grub` → `chroot ... grub2-mkconfig -o /boot/grub2/grub.cfg` |
| `src/modules/amd.json` | 31 | `["update-grub"]` → `["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"]` |
| `src/tabs/terminal_actions.py` | 58–59 | Алиасы `upgrub`/`grubup` |
| `src/tabs/terminal.py` | 63–64 | Алиас `upgrub` |

### 4.2 `remove-old-kernels`
| Файл | Строки | Замена |
|---|---|---|
| `src/tabs/terminal.py` | 44 | `sudo remove-old-kernels -a` → `sudo dnf remove $(rpm -qa kernel-core\* \| sort -V \| head -n -2)` |

### 4.3 Путь `/etc/altlinux-release`
| Файл | Строки | Замена |
|---|---|---|
| `src/tabs/setup.py` | 82 | `/etc/altlinux-release` → `/etc/fedora-release` |
| `src/tabs/tweaks.py` | 104 | `/etc/altlinux-release` → `/etc/fedora-release` |

### 4.4 Путь `/etc/apt/sources.list.d/`
| Файл | Строки | Замена |
|---|---|---|
| `src/tabs/setup.py` | 22 | Удалить `_SOURCES_DIR` |
| `src/tabs/tweaks.py` | 116–131 | Удалить `_detect_branch()` (парсит `.list`) |
| `src/tabs/tweaks.py` | 434, 442, 502 | Удалить команды бэкапа/восстановления `.list` файлов |

---

## Фаза 5: UI, rebranding и косметика

### 5.1 Название и брендинг
| Файл | Действие |
|---|---|
| `src/altbooster.py` | `application_id="ru.altbooster.app"` → `"org.fedorabooster.app"` |
| `src/altbooster.py` | `"ALT Booster"` → `"Fedora Booster"` |
| `src/ui/window.py` | `"ALT Booster"` → `"Fedora Booster"` |
| `install.sh` | Название, комментарии, лого-арт |
| `Makefile` | `NAME=altbooster` → `NAME=fedorabooster` |
| `pyproject.toml` | `name = "altbooster"` → `name = "fedorabooster"`, описание |
| `README.md` | Полный рерайт под Fedora |
| `.desktop` файл | `Name=ALT Booster` → `Name=Fedora Booster`, `StartupWMClass=ru.altbooster.app` → `org.fedorabooster.app` |

### 5.2 URL и ссылки
| Файл | Действие |
|---|---|
| `src/ui/window.py` | `_ALT_ZERO_GUIDE_URL` → документация Fedora Booster |
| `src/tabs/tweaks.py` | `_ALT_ZERO_GUIDE_URL` → убрать/заменить |
| `pyproject.toml` | Homepage/Repository → новый GitHub repo |

### 5.3 Удаление ALT-специфичных строк
| Файл | Описание |
|---|---|
| `src/core/mirror.py:347, 434` | `"LiveUSB ALT Linux"` → `"LiveUSB Fedora"` |
| `src/tabs/setup.py:24` | `"ALT Linux (ftp.altlinux.org)"` → Удалить строку зеркала |
| `src/tabs/scx_sched_ext.py:53` | `"в каталоге пакетов ALT"` → `"в репозиториях"` |
| `src/tabs/scx_sched_ext.py:140` | `"ALT Booster"` → `"Fedora Booster"` |
| `src/tabs/system76_scheduler.py:195` | `"(ALT: rust, rust-cargo...)"` → `"(Fedora: rust, cargo...)"` |

### 5.4 Глобальный поиск
| Файл | Действие |
|---|---|
| `src/ui/global_search.py` | Удалить `"eepm"`, `"sudowheel"`, `"control"`, `"Sisyphus"` из поисковых ключевых слов |
| `src/ui/global_search.py` | Удалить пункты "Установить EPM", "Обновить систему (EPM)" |

### 5.5 Вкладка Tweaks — переработка UI
| Действие | Описание |
|---|---|
| Удалить подвкладку "Общие твики" | Или переименовать; Sisyphus-секция удалена |
| Переименовать "Платформа (p10, p11, …) и Сизиф" | → "Платформа" или удалить |
| CSS-классы | Убрать `.ab-tweak-sisyphus-badge`, `.ab-tweak-branch-badge-*` |

---

---

## Фаза 6: Каталог расширений GNOME Shell

*Полная замена каталога RECOMMENDED на список пользователя + поддержка GitHub-расширений.*

### 6.0 Текущее состояние

Сейчас в `tabs/extensions.py` (1140 строк) жёстко зашит список `RECOMMENDED` из **13 расширений**.  
Установка расширений происходит тремя методами:

| Метод | Инструмент | Источник |
|--------|-----------|----------|
| A | `gext` (gnome-extensions-cli) | GNOME Extensions API |
| B | Native fallback (`gnome-extensions install`) | GNOME Extensions API |
| C | `epm install` (ALT Linux) | RPM-пакеты ALT → **УДАЛИТЬ** |

### 6.1 Итоговый каталог RECOMMENDED (20 расширений)

5 уже есть в каталоге + 12 новых + 2 с GitHub + 1 новый метод установки.

#### Уже в каталоге (5 — оставить)

| # | UUID | Название | PK |
|---|------|----------|-----|
| 1 | `appindicatorsupport@rgcjonas.gmail.com` | AppIndicator and KStatusNotifierItem | 615 |
| 2 | `Vitals@CoreCoding.com` | Vitals | 1460 |
| 3 | `just-perfection-desktop@just-perfection` | Just Perfection | 3843 |
| 4 | `blur-my-shell@aunetx` | Blur my Shell | 3193 |
| 5 | `right-click-next@derVedro` | Right Click Next | 7600 |

#### Добавить из GNOME Extensions (11)

| # | UUID | Название | PK |
|---|------|----------|-----|
| 6 | `caffeine@patapon.info` | Caffeine | 517 |
| 7 | `clipboard-indicator@tudmotu.com` | Clipboard Indicator | 779 |
| 8 | `compiz-alike-magic-lamp-effect@hermes83.github.com` | Compiz alike magic lamp effect | 3740 |
| 9 | `date-menu-formatter@marcinjakubowski.github.com` | Date Menu Formatter | 4655 |
| 10 | `status-area-horizontal-spacing@mathematical.coffee.gmail.com` | Status Area Horizontal Spacing | 355 |
| 11 | `tilingshell@ferrarodomenico.com` | Tiling Shell | 7065 |
| 12 | `tweaks-system-menu@extensions.gnome.org` | Tweaks & Extensions in System Menu | 1653 |
| 13 | `weatherornot@somepaulo.github.io` | Weather or Not | 5660 |
| 14 | `windowIsReady_Remover@nunofarruca` | Window Is Ready Notification Remover | 1007 |
| 15 | `advanced-weather-companion@timur@linux.com` | Advanced Weather Companion | 7603 |
| 16 | `transcodeappsearch@marmistrz` | Transcode App Search | 928 |

Все 11 устанавливаются стандартными методами (A: `gext install <pk>` или B: `gnome-extensions install` через API `extensions.gnome.org`).

#### Добавить из GitHub (2 — требуют нового метода установки)

| # | UUID | Название | GitHub-репозиторий | Метод установки |
|---|------|----------|-------------------|-----------------|
| 17 | `zorkiy@toxblh.ru` | Zorkiy | `https://github.com/Toxblh/gnome-shell-extension-zorkiy` | `git clone` + `./install.sh` |
| 18 | `icon-matcher@peppodev` | Icon Matcher | `https://github.com/PeppoDev/icon-matcher` | `git clone` + `.scripts/install.sh` |

#### Удалить из старого каталога (8 — не в списке пользователя)

Dash to Dock (307), Dash to Panel (1160), Pigeon Email (9301), Auto Accent Colour (7502), Rounded Window Corners Reborn (7048), Desktop Icons NG (2087), No Overview at Startup (4099), Status Tray (9164).

### 6.2 `tabs/extensions.py` — переработка

#### Удалить
| Действие | Строки | Описание |
|---|---|---|
| Удалить строки с PK 307, 1160, 9301, 7502, 7048, 2087, 4099, 9164 | 32–111 | 8 расширений из старого списка RECOMMENDED |
| Удалить метод C (EPM-установка) | 940–960 | `_on_install_ext()` с `epm:...` install_id — ALT-specific |
| Удалить `apt-get install pip` из `_ensure_gext()` | 604–620 | Заменить на `dnf install python3-pip` |

#### Добавить
| Действие | Описание |
|---|---|
| Добавить 11 новых записей в `RECOMMENDED` | UUID, название, описание (на русском), PK |
| Добавить запись для **Zorkiy** | `type: "github"`, URL репозитория, UUID `zorkiy@toxblh.ru` |
| Добавить запись для **Icon Matcher** | `type: "github"`, URL репозитория, UUID `icon-matcher@peppodev` |
| Добавить метод D: **установка из GitHub** | Новая функция `_install_from_github(repo_url, uuid)` |
| Обновить `_search_extensions()` | интегрировать GitHub-расширения в поиск |
| Обновить `_is_ext_installed()` | проверять UUID в `~/.local/share/gnome-shell/extensions/<uuid>/` |

### 6.3 Метод D: установка из GitHub (новый)

```python
def _install_from_github(self, repo_url: str, uuid: str) -> bool:
    """
    Клонирует репозиторий во временную папку,
    копирует директорию расширения в ~/.local/share/gnome-shell/extensions/<uuid>/,
    включает расширение через gnome-extensions enable <uuid>.
    """
```

Алгоритм:
1. `git clone --depth=1 <repo_url> /tmp/altbooster-ext-XXXX/`
2. Найти директорию с `metadata.json` и `extension.js`
3. `mkdir -p ~/.local/share/gnome-shell/extensions/<uuid>/`
4. `cp -r <source_dir>/* ~/.local/share/gnome-shell/extensions/<uuid>/`
5. `gnome-extensions enable <uuid>`
6. Удалить временную папку

**Особенности Zorkiy**:
- UUID: `zorkiy@toxblh.ru` (имя директории в репозитории)
- Требует `system76-scheduler` для работы (документировать в описании)

**Особенности Icon Matcher**:
- UUID: `icon-matcher@peppodev` (упомянут в README)
- Устанавливается через `.scripts/install.sh` ИЛИ ручным копированием `extension.js` + `metadata.json`

### 6.4 `_ensure_gext()` — замена apt-get на dnf

| Строки | Было | Стало |
|--------|------|-------|
| 604–620 | `apt-get install -y pip python3-module-pip` | `dnf install -y python3-pip` |
| 604–620 | `pip install gnome-extensions-cli --user` | без изменений |

### 6.5 `ui/global_search.py` — обновление ключевых слов

| Действие | Описание |
|---|---|
| Добавить поисковые ключи | `"zorkiy"`, `"icon-matcher"`, `"caffeine"`, `"clipboard"`, `"compiz"`, `"tiling"`, `"weather"` |
| Удалить поисковые ключи | Удалённые из каталога расширения |
| Обновить `_extension_catalog_items()` | Учесть новый тип `"github"` в записях |

### 6.6 Удаление из старого каталога расширений — влияние на другие вкладки

| Файл | Действие |
|---|---|
| `tabs/tweaks.py` (стр. 195–199) | `is_drive_menu_patched()` + `patch_drive_menu()` — **оставить**, это системный патч, не расширение из каталога |
| `core/checks.py` (стр. 193) | `is_drive_menu_patched()` — **оставить** |
| `core/tweaks.py` (стр. 15–79) | `patch_drive_menu()` — **оставить** |
| `core/borg.py` (стр. 787–807) | `generate_extensions_meta()` — без изменений (работает с установленными расширениями) |

### 6.7 Файлы, затрагиваемые в фазе 6

| Файл | Описание изменений |
|---|---|
| `src/tabs/extensions.py` | **Крупнейшая переработка** — новый каталог, новый метод установки GitHub, удаление EPM-метода |
| `src/ui/global_search.py` | Новые поисковые ключи, удаление старых |
| `src/tabs/tweaks.py` | Без изменений (Drive menu patch остаётся) |
| `core/checks.py` | Без изменений |
| `core/tweaks.py` | Без изменений |

### 6.8 Оценка: **3 часа**

---

## Фаза 7: Скрипты установки и инфраструктура

### 7.1 `install.sh`
| Строки | Действие |
|---|---|
| 2 | `# ALT Booster — Install Script` → `# Fedora Booster — Install Script` |
| 16–18 | `"ALT Booster разработан для GNOME."` → `"Fedora Booster разработан для GNOME."` |
| 25 | Убрать комментарий про ALT Linux и sudo |
| 49–50 | Заменить `python3-module-pygobject3` + `libgtk4-gir` → `python3-gobject` + `gtk4` |
| 51–52 | Заменить `libadwaita-gir` → `libadwaita` |
| 56 | `apt-get install -y` → `dnf install -y` |
| 87–89 | `Name=ALT Booster`, `Comment=` → Fedora-варианты |
| 95 | Keywords: убрать `apt`, добавить `dnf` |
| 118 | `"ALT Booster успешно установлен!"` → `"Fedora Booster успешно установлен!"` |

### 7.2 `uninstall.sh`
| Строки | Действие |
|---|---|
| 2, 13, 21 | Замена названий ALT → Fedora |

### 7.3 `Makefile`
| Строки | Действие |
|---|---|
| 1, 3 | `NAME=altbooster` → `NAME=fedorabooster` |

### 7.4 `pyproject.toml`
| Строки | Действие |
|---|---|
| 6 | `name = "altbooster"` → `"fedorabooster"` |
| 8 | `description` — обновить |
| 15–17 | URLs на новый репозиторий |
| 20 | `altbooster = "altbooster:main"` → `fedorabooster = "fedorabooster:main"` |
| 23 | `"altbooster"` → `"fedorabooster"` |
| 24 | `py-modules = ["altbooster"]` → `"fedorabooster"` |

---

## Фаза 8: Code Quality & Рефакторинг

### 8.1 Удаление мёртвого кода
- Убрать все неиспользуемые импорты после замен
- Удалить `run_epm`/`run_epm_sync` из `backend.py`
- Удалить `is_epm_installed` отовсюду
- Удалить `_wrap_epm_auto_install`
- Удалить `_is_sisyphus`, `_detect_branch` из tweaks.py/setup.py
- Удалить `_MIRRORS`, `_detect_active_mirror`, `_build_mirror_switch_cmd` из setup.py

### 8.2 Линтинг
- Прогнать `ruff check .` и исправить ошибки
- Убедиться, что `E501` (длинные строки) в bash-командах по-прежнему разрешён

### 8.3 Типизация
- Проверить аннотации в изменённых функциях
- Убедиться, что `from __future__ import annotations` есть в новых/изменённых модулях

---

## Фаза 9: Тестирование на Fedora

### 9.1 Smoke-test
- Установка на чистую Fedora 41 GNOME
- Проверка: старт приложения, авторизация pkexec
- Проверка: каждая вкладка открывается без ошибок
- Проверка: установка пакетов через dnf
- Проверка: удаление пакетов через dnf
- Проверка: Flatpak-операции
- Проверка: BorgBackup, Btrfs
- Проверка: DaVinci Resolve (если доступен)

### 9.2 Edge cases
- DNF lock: проверить определение занятого менеджера
- Смена репозиториев (если осталась)
- Права sudo (wheel group)
- Обновление системы через UI

### 9.3 Известные риски
- Некоторые пакеты могут отсутствовать в Fedora-репах (ananicy-cpp, scx-scheds) — тогда их секции нужно скрыть или убрать
- RPM Fusion может потребоваться для ffmpeg, ROCm, DaVinci
- Названия пакетов в apps.json нужно верифицировать на реальном Fedora

---

## Сводная таблица затрагиваемых файлов

| Файл | Фаз(ы) | Тип изменений |
|---|---|---|
| `src/core/privileges.py` | 1 | Удаление EPM, замена APT-локов |
| `src/core/packages.py` | 1 | DNF-парсинг, замена apt-get |
| `src/core/checks.py` | 1, 2 | Удаление EPM, замена control sudowheel, DNF-локи |
| `src/core/config.py` | 1 | DNF_LOCK_FILES |
| `src/core/backend.py` | 1 | Импорты run_dnf |
| `src/core/sched_ext.py` | 1 | Название пакета ядра |
| `src/core/mirror.py` | 4 | update-grub |
| `src/tabs/setup.py` | 2, 4, 5 | **Крупнейшая переработка** — удаление EPM, зеркал, Sisyphus, control sudowheel |
| `src/tabs/tweaks.py` | 2, 4, 5 | **Крупнейшая переработка** — удаление ~300 строк Sisyphus |
| `src/tabs/extensions.py` | 6 | **Крупнейшая переработка** — новый каталог (20 расширений), GitHub-установка, удаление EPM-метода |
| `src/tabs/apps.py` | 2, 3 | Замена веток p11/Sisyphus, API URL |
| `src/tabs/flatpak.py` | 2, 3 | fedora-specific flatpak установка |
| `src/tabs/terminal.py` | 2, 3, 4, 5 | Замена apt-get/epm/update-grub/remove-old-kernels |
| `src/tabs/terminal_actions.py` | 2, 4, 5 | Алиасы |
| `src/tabs/davinci.py` | 3 | Названия пакетов ROCm/FFmpeg |
| `src/tabs/intel.py` | 3 | Названия пакетов |
| `src/tabs/system76_scheduler.py` | 3 | Названия пакетов, документация |
| `src/tabs/scx_sched_ext.py` | 5 | Текст |
| `src/tabs/timesync/page.py` | 3 | `borg` → `borgbackup` |
| `src/ui/global_search.py` | 5, 6 | Удаление ALT-ключевых слов + новые ключи расширений |
| `src/ui/window.py` | 5 | Rebranding |
| `src/ui/dialogs.py` | 1 | Тип источника `dnf` |
| `src/ui/dynamic_page.py` | 1 | `kind == "epm"` → `kind == "privileged"` |
| `src/ui/rows.py` | 1 | Замена apt-get update → dnf makecache, epm → dnf |
| `src/altbooster.py` | 5 | Rebranding |
| `src/modules/maintenance.json` | 2 | apt-get clean → dnf clean all |
| `src/modules/terminal.json` | 2, 3 | apt-get/epm → dnf, названия пакетов |
| `src/modules/amd.json` | 2, 4 | epm → dnf, update-grub |
| `src/modules/apps.json` | 2, 3 | apt-get/epm → dnf, названия пакетов |
| `install.sh` | 3, 7 | Зависимости, rebranding |
| `uninstall.sh` | 7 | Rebranding |
| `Makefile` | 7 | Rebranding |
| `pyproject.toml` | 7 | Rebranding, метаданные |
| `README.md` | 5 | Полный рерайт |
| `CHANGELOG.md` | 5 | Запись о Fedora-порте |

---

## Оценка трудозатрат

| Фаза | Описание | Оценка |
|---|---|---|
| 0 | Подготовка | 0.5 ч |
| 1 | core/ — пакетный менеджер и привилегии | 3 ч |
| 2 | Репозитории и дистрибутив | 5 ч |
| 3 | Названия пакетов | 2 ч |
| 4 | Системные команды и пути | 1 ч |
| 5 | UI и rebranding | 2 ч |
| 6 | Каталог расширений GNOME Shell | 3 ч |
| 7 | Скрипты установки | 1 ч |
| 8 | Code quality | 1 ч |
| 9 | Тестирование | 3 ч |
| **Итого** | | **~21.5 ч** |

---

## Порядок выполнения (критический путь)

1. **Фаза 1** (core/) — без неё ничего не работает
2. **Фаза 3** (названия пакетов) — параллельно с фазой 1, т.к. это lookup-таблица
3. **Фаза 2** (tabs/setup.py, tabs/tweaks.py) — самая объёмная
4. **Фаза 4** (системные команды)
5. **Фаза 5 + 7** (rebranding + скрипты) — можно параллельно с фазой 2
6. **Фаза 6** (каталог расширений) — можно параллельно с фазой 5, т.к. независима от dnf/core
7. **Фаза 8** (linting)
8. **Фаза 9** (тестирование)
