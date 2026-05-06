
import ast
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from core import backend, config
from ui.install_preview_dialog import InstallPreviewDialog
from ui.rows import SettingRow
from ui.widgets import make_button, make_icon, make_scrolled_page, scroll_child_into_view


def _make_channel_badge(channel: str) -> Gtk.Label:
    lbl = Gtk.Label(label=channel)
    lbl.add_css_class("ab-source-badge")
    if channel == "stable":
        lbl.add_css_class("success")
    elif channel == "beta":
        lbl.add_css_class("warning")
    elif channel == "alpha":
        lbl.add_css_class("error")
    lbl.set_valign(Gtk.Align.CENTER)
    return lbl


class SetupPage(Gtk.Box):
    def __init__(self, log_fn):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._log = log_fn

        scroll, body = make_scrolled_page()
        self._body = body
        self.append(scroll)
        self._build_system_group(body)
        self._build_filemanager_group(body)
        self._build_keyboard_group(body)
        self._register_setup_search_targets()

    @staticmethod
    def _is_newer(version, current):
        if not version:
            return False
        try:
            def _nums(v):
                return [int(x) for x in v.split("-")[0].split(".")]
            cur, lat = _nums(current), _nums(version)
            max_len = max(len(cur), len(lat))
            cur += [0] * (max_len - len(cur))
            lat += [0] * (max_len - len(lat))
            return lat > cur
        except ValueError:
            return False

    def _on_gnome_software_updates(self, row):
        row.set_working()
        self._log("\n▶  Оптимизация Центра приложений (отключение download-updates)...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Настройка GNOME Software...")

        def _do():
            ok = backend.run_gsettings(["set", "org.gnome.software", "download-updates", "false"])
            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._log, "✔  Фоновая загрузка пакетов отключена. Применяется сразу, перезагрузка не нужна.\n" if ok else "✘  Ошибка применения настроек GNOME\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)

        threading.Thread(target=_do, daemon=True).start()

    def _on_gnome_software_updates_undo(self, row):
        row.set_working()
        self._log("\n▶  Включение автообновлений GNOME Software...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Настройка GNOME Software...")

        def _do():
            ok = backend.run_gsettings(["set", "org.gnome.software", "download-updates", "true"])
            GLib.idle_add(row.set_undo_done, ok)
            GLib.idle_add(self._log, "✔  Автообновления включены.\n" if ok else "✘  Ошибка\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
        threading.Thread(target=_do, daemon=True).start()

    def _on_epm(self, row):
        row.set_working()
        win = self.get_root()

        if backend.is_system_busy():
            msg = "GNOME Software или PackageKit обновляет базу в фоне — операция будет ждать освобождения"
            self._log(f"\n⚠  {msg}\n")
            if hasattr(win, "add_toast"):
                t = Adw.Toast(title=msg)
                t.set_timeout(8)
                GLib.idle_add(win.add_toast, t)

        self._log("\n▶  Обновление системы...\n")
        if hasattr(win, "start_progress"):
            win.start_progress("Обновление системы...")

        def on_full_upgrade_done(ok):
            GLib.idle_add(row.set_done, False)
            GLib.idle_add(row._btn.set_label, "Обновить")
            if ok:
                self._log("\n✔  Fedora обновлена!\n")
            else:
                self._log("\n✘  Ошибка обновления\n")
            if hasattr(win, "stop_progress"):
                win.stop_progress(ok)

        def _run_full_upgrade():
            self._log("\n▶  dnf upgrade...\n")
            backend.run_privileged(["dnf", "upgrade", "-y"], self._log, on_full_upgrade_done)

        def on_update_done(ok):
            if not ok:
                GLib.idle_add(row.set_done, False)
                GLib.idle_add(row._btn.set_label, "Обновить")
                self._log("\n✘  Ошибка обновления индексов\n")
                if hasattr(win, "stop_progress"):
                    win.stop_progress(False)
                return

            def on_confirm():
                _run_full_upgrade()

            def on_cancel():
                self._log("\n⚠  Обновление отменено пользователем.\n")
                GLib.idle_add(row.set_done, False)
                GLib.idle_add(row._btn.set_label, "Обновить")
                if hasattr(win, "stop_progress"):
                    win.stop_progress(False)

            def on_no_changes():
                GLib.idle_add(row.set_done, False)
                GLib.idle_add(row._btn.set_label, "Обновить")
                if hasattr(win, "stop_progress"):
                    win.stop_progress(True)

            GLib.idle_add(
                lambda: InstallPreviewDialog(
                    parent=self.get_root(),
                    app_name="Обновление системы",
                    source_label="DNF",
                    cmd=["dnf", "upgrade"],
                    on_confirm=on_confirm,
                    on_cancel=on_cancel,
                    on_no_changes=on_no_changes,
                    runner=backend.run_privileged_sync,
                    empty_message="Система и приложения обновлены",
                    log=self._log,
                    no_changes_message="ℹ  Система актуальна — обновлений нет.\n",
                ).present()
            )

        backend.run_privileged(["dnf", "makecache", "-y"], self._log, on_update_done)

    def _build_system_group(self, body):
        pkg_group = Adw.PreferencesGroup()
        pkg_group.set_title("Обновление и пакеты")
        body.append(pkg_group)

        self._r_epm = SettingRow(
            "software-update-available-symbolic", "Обновить систему (DNF)",
            "Выполняет dnf makecache и dnf upgrade", "Обновить",
            self._on_epm, lambda: False, "", "Обновлено",
        )
        pkg_group.add(self._r_epm)

        sys_group = Adw.PreferencesGroup()
        sys_group.set_title("Система")
        body.append(sys_group)

        sys_rows = [
            ("view-refresh-symbolic",    "Автообновление GNOME Software",      "Отключаем фоновую загрузку GNOME Software", "Отключить",    self._on_gnome_software_updates, lambda: backend.gsettings_get("org.gnome.software", "download-updates") == "false", "setting_gnome_software_updates", "Выключено", self._on_gnome_software_updates_undo, "Включить"),
            ("media-flash-symbolic",               "Автоматический TRIM",         "Включает еженедельную очистку блоков SSD",      "Включить",     self._on_trim_timer,           backend.is_fstrim_enabled,             "setting_trim_auto", "Активировано", self._on_trim_timer_undo, "Отключить"),
            ("document-open-recent-symbolic",      "Лимиты журналов",             "SystemMaxUse=100M и сжатие в journald.conf",    "Настроить",    self._on_journal_limit,  backend.is_journal_optimized,          "setting_journal_opt", "Активировано", self._on_journal_limit_undo, "Сбросить"),
            ("video-display-symbolic",             "Дробное масштабирование",     "Включает scale-monitor-framebuffer",            "Включить",     self._on_scale,          backend.is_fractional_scaling_enabled, "setting_scale", "Активировано", self._on_scale_undo, "Отключить"),
        ]

        self._r_gnome_sw, self._r_trim, self._r_journal, self._r_scale = [
            SettingRow(*r) for r in sys_rows
        ]

        for r in (
            self._r_gnome_sw,
            self._r_trim,
            self._r_journal,
            self._r_scale
        ):
            sys_group.add(r)

    def _build_filemanager_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("Файловый менеджер Nautilus и иконки")
        body.append(group)

        def _check_nautilus():
            try:
                sort = backend.gsettings_get("org.gtk.gtk4.Settings.FileChooser", "sort-directories-first")
                links = backend.gsettings_get("org.gnome.nautilus.preferences", "show-create-link")
                return "true" in sort.lower() and "true" in links.lower()
            except Exception:
                return False

        self._papirus_row = self._create_papirus_row()

        filemanager_rows = [
            ("folder-symbolic",    "Настройка Nautilus",    "Сортировка папок первыми, создание ссылок, удаление",  "Включить",  self._on_nautilus,              _check_nautilus,                        "setting_nautilus", "Активировано", self._on_nautilus_undo, "Отключить"),
            ("media-flash-symbolic", "Кэш копирования",      "vm.dirty_bytes/background_bytes = 64 MB (ускоряет копирование)", "Включить",  self._on_vm_dirty,             backend.is_vm_dirty_optimized,           "setting_vm_dirty", "Активировано", self._on_vm_dirty_undo, "Отключить"),
            ("folder-symbolic",      "Sushi — предпросмотр",  "Быстрый предпросмотр файлов через пробел в Nautilus",     "Установить", self._on_install_sushi,         lambda: backend.check_app_installed({"check": ["rpm", "sushi"]}), "setting_sushi", "Установлено", self._on_remove_sushi, "Удалить"),
            ("folder-symbolic",      "f3d — 3D превью",       "Предпросмотр 3D-моделей прямо в Nautilus",                "Установить", self._on_install_f3d,           lambda: backend.check_app_installed({"check": ["rpm", "f3d"]}), "setting_f3d", "Установлено", self._on_remove_f3d, "Удалить"),
        ]

        self._r_naut, self._r_dirty, self._r_sushi, self._r_f3d = [
            SettingRow(*r) for r in filemanager_rows
        ]

        for r in (self._papirus_row, self._r_naut, self._r_dirty, self._r_sushi, self._r_f3d):
            group.add(r)

    def _on_nautilus(self, row):
        row.set_working()
        self._log("\n▶  Применение настроек Nautilus...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Настройка Nautilus...")
        def _do():
            ok1 = backend.run_gsettings(["set", "org.gtk.gtk4.Settings.FileChooser", "sort-directories-first", "true"])
            ok2 = backend.run_gsettings(["set", "org.gnome.nautilus.icon-view", "captions", "['size', 'date_modified', 'none']"])
            ok3 = backend.run_gsettings(["set", "org.gnome.nautilus.preferences", "show-create-link", "true"])
            ok4 = backend.run_gsettings(["set", "org.gnome.nautilus.preferences", "show-delete-permanently", "true"])
            ok = ok1 and ok2 and ok3 and ok4
            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._log, "✔  Настройки Nautilus применены!\n" if ok else "✘  Ошибка\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
        threading.Thread(target=_do, daemon=True).start()

    def _on_nautilus_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс настроек Nautilus...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Сброс настроек Nautilus...")
        def _do():
            ok1 = backend.run_gsettings(["reset", "org.gtk.gtk4.Settings.FileChooser", "sort-directories-first"])
            ok2 = backend.run_gsettings(["reset", "org.gnome.nautilus.icon-view", "captions"])
            ok3 = backend.run_gsettings(["reset", "org.gnome.nautilus.preferences", "show-create-link"])
            ok4 = backend.run_gsettings(["reset", "org.gnome.nautilus.preferences", "show-delete-permanently"])
            ok = ok1 and ok2 and ok3 and ok4
            GLib.idle_add(row.set_undo_done, ok)
            GLib.idle_add(self._log, "✔  Настройки Nautilus сброшены!\n" if ok else "✘  Ошибка\n")
        threading.Thread(target=_do, daemon=True).start()

    def _on_vm_dirty(self, row):
        row.set_working()
        self._log("\n▶  Настройка кэша копирования (vm.dirty)...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Настройка vm.dirty...")
        backend.apply_vm_dirty(self._log,
            lambda ok: (row.set_done(ok), self._log("✔  Кэш копирования исправлен!\n" if ok else "✘  Ошибка\n"), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _on_vm_dirty_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс настроек vm.dirty...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Сброс vm.dirty...")
        backend.run_privileged(["rm", "-f", "/etc/sysctl.d/99-fedorabooster.conf"], self._log,
            lambda ok: (row.set_undo_done(ok), self._log("✔  Настройки сброшены (требуется перезагрузка для эффекта)\n" if ok else "✘  Ошибка\n"), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _on_install_sushi(self, row):
        row.set_working()
        self._log("\n▶  Установка Sushi (предпросмотр)...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка Sushi...")
        def _done(ok):
            row.set_done(ok)
            if ok:
                self._log("✔  Sushi установлен! Перезапускаю Nautilus...\n")
            else:
                self._log("✘  Ошибка установки Sushi\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
            if ok: subprocess.run(["nautilus", "-q"])
        backend.run_privileged(["dnf", "install", "-y", "sushi"], self._log, _done)

    def _on_remove_sushi(self, row):
        row.set_working()
        self._log("\n▶  Удаление Sushi...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление Sushi...")
        def _done(ok):
            row.set_undo_done(ok)
            self._log("✔  Sushi удалён!\n" if ok else "✘  Ошибка удаления Sushi\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
            if ok: subprocess.run(["nautilus", "-q"])
        backend.run_privileged(["dnf", "remove", "-y", "sushi"], self._log, _done)

    def _on_install_f3d(self, row):
        row.set_working()
        self._log("\n▶  Установка f3d (3D превью)...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка f3d...")

        cmd = ["dnf", "install", "-y", "f3d"]

        def _final_done(ok):
            row.set_done(ok)
            if ok:
                self._log("✔  f3d установлен! Очищаю кэш миниатюр и перезапускаю Nautilus...\n")
                if hasattr(win, "stop_progress"): win.stop_progress(ok)
                try:
                    shutil.rmtree(os.path.expanduser("~/.cache/thumbnails"), ignore_errors=True)
                except Exception:
                    pass
                subprocess.run(["nautilus", "-q"])
            else:
                self._log("✘  Не удалось установить f3d. Возможно, пакет отсутствует в репозитории.\n")
                if hasattr(win, "stop_progress"): win.stop_progress(ok)

        def _retry_install_after_update(ok):
            if not ok:
                self._log("✘  Ошибка обновления индексов.\n")
                _final_done(False)
                return
            self._log("\n▶  Повторная попытка установки f3d (после makecache)...\n")
            backend.run_privileged(cmd, self._log, _final_done)

        def _first_attempt_done(ok):
            if ok:
                _final_done(True)
            else:
                self._log("\n⚠  Ошибка установки. Пробую обновить индексы (dnf makecache)...\n")
                backend.run_privileged(["dnf", "makecache", "-y"], self._log, _retry_install_after_update)

        backend.run_privileged(cmd, self._log, _first_attempt_done)

    def _on_remove_f3d(self, row):
        row.set_working()
        self._log("\n▶  Удаление f3d...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление f3d...")
        def _done(ok):
            row.set_undo_done(ok)
            self._log("✔  f3d удалён!\n" if ok else "✘  Ошибка удаления f3d\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
            if ok: subprocess.run(["nautilus", "-q"])
        backend.run_privileged(["dnf", "remove", "-y", "f3d"], self._log, _done)


    def _build_keyboard_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("Раскладка клавиатуры")
        body.append(group)

        self._r_alt = SettingRow(
            "input-keyboard-symbolic", "Alt + Shift",
            "Классическое переключение раскладки", "Включить",
            self._on_altshift, None, "setting_kbd_altshift", done_label="Активно",
            on_undo=self._on_altshift_undo, undo_label="Сбросить", undo_icon="edit-undo-symbolic",
        )
        self._r_caps = SettingRow(
            "input-keyboard-symbolic", "CapsLock",
            "Переключение раскладки кнопкой CapsLock", "Включить",
            self._on_capslock, None, "setting_kbd_capslock", done_label="Активно",
            on_undo=self._on_capslock_undo, undo_label="Сбросить", undo_icon="edit-undo-symbolic",
        )
        self._r_ctrl = SettingRow(
            "input-keyboard-symbolic", "Ctrl + Shift",
            "Переключение раскладки по Ctrl+Shift", "Включить",
            self._on_ctrlshift, None, "setting_kbd_ctrlshift", done_label="Активно",
            on_undo=self._on_ctrlshift_undo, undo_label="Сбросить", undo_icon="edit-undo-symbolic",
        )
        self._r_win = SettingRow(
            "input-keyboard-symbolic", "Win + Space",
            "Стандартное переключение раскладки GNOME", "Включить",
            self._on_winspace, None, "setting_kbd_winspace", done_label="Активно",
            on_undo=self._on_winspace_undo, undo_label="Сбросить", undo_icon="edit-undo-symbolic",
        )
        group.add(self._r_alt)
        group.add(self._r_caps)
        group.add(self._r_ctrl)
        group.add(self._r_win)
        threading.Thread(target=self._detect_kbd_mode, daemon=True).start()

    def _register_setup_search_targets(self):
        self._setup_search_targets = {
            "epm_update": self._r_epm,
            "gnome_sw": self._r_gnome_sw,
            "trim": self._r_trim,
            "journal": self._r_journal,
            "scale": self._r_scale,
            "papirus": self._papirus_row,
            "nautilus": self._r_naut,
            "vm_dirty": self._r_dirty,
            "sushi": self._r_sushi,
            "f3d": self._r_f3d,
            "kbd_altshift": self._r_alt,
            "kbd_caps": self._r_caps,
            "kbd_ctrlshift": self._r_ctrl,
            "kbd_winspace": self._r_win,
        }

    def focus_search_target(self, key: str) -> bool:
        w = self._setup_search_targets.get(key)
        if w is None:
            return False
        scroll = self.get_first_child()
        if isinstance(scroll, Gtk.ScrolledWindow):
            scroll_child_into_view(scroll, w)
        GLib.idle_add(w.grab_focus)
        return True

    def _on_trim_timer(self, row):
        row.set_working()
        self._log("\n▶  Включение fstrim.timer...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Включение TRIM...")
        backend.run_privileged(
            ["systemctl", "enable", "--now", "fstrim.timer"],
            self._log,
            lambda ok: (row.set_done(ok), self._log("✔  TRIM включён!\n" if ok else "✘  Ошибка\n"), win.stop_progress(ok) if hasattr(win, "stop_progress") else None),
        )

    def _on_trim_timer_undo(self, row):
        row.set_working()
        self._log("\n▶  Отключение fstrim.timer...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Отключение TRIM...")
        backend.run_privileged(
            ["systemctl", "disable", "--now", "fstrim.timer"],
            self._log,
            lambda ok: (row.set_undo_done(ok), self._log("✔  TRIM отключён!\n" if ok else "✘  Ошибка\n"), win.stop_progress(ok) if hasattr(win, "stop_progress") else None),
        )

    def _on_journal_limit(self, row):
        row.set_working()
        self._log("\n▶  Оптимизация журналов (создание drop-in конфига)...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Настройка журналов...")
        cmd = [
            "bash", "-c",
            "mkdir -p /etc/systemd/journald.conf.d && "
            "echo -e '[Journal]\\nSystemMaxUse=100M\\nCompress=yes' "
            "> /etc/systemd/journald.conf.d/99-fedorabooster.conf && "
            "systemctl restart systemd-journald",
        ]
        backend.run_privileged(
            cmd, self._log,
            lambda ok: (row.set_done(ok), self._log("✔  Лимиты применены через drop-in!\n" if ok else "✘  Ошибка\n"), win.stop_progress(ok) if hasattr(win, "stop_progress") else None),
        )

    def _on_journal_limit_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс настроек журнала...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Сброс настроек журнала...")
        backend.run_privileged(
            ["bash", "-c", "rm -f /etc/systemd/journald.conf.d/99-fedorabooster.conf && systemctl restart systemd-journald"],
            self._log,
            lambda ok: (row.set_undo_done(ok), self._log("✔  Настройки журнала сброшены!\n" if ok else "✘  Ошибка\n"), win.stop_progress(ok) if hasattr(win, "stop_progress") else None),
        )

    def _on_scale(self, row):
        row.set_working()
        self._log("\n▶  Масштабирование...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Включение масштабирования...")

        def _do():
            current = backend.gsettings_get(config.GSETTINGS_MUTTER, "experimental-features")
            try:
                feats = ast.literal_eval(current) if current not in ("@as []", "[]", "") else []
            except (ValueError, SyntaxError):
                feats = []
            if "scale-monitor-framebuffer" not in feats:
                feats.append("scale-monitor-framebuffer")
            ok = backend.run_gsettings(
                ["set", config.GSETTINGS_MUTTER, "experimental-features", str(feats)]
            )
            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._log, "✔  Включено!\n" if ok else "✘  Ошибка\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)

        threading.Thread(target=_do, daemon=True).start()

    def _on_scale_undo(self, row):
        row.set_working()
        self._log("\n▶  Отключение масштабирования...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Отключение масштабирования...")
        def _do():
            current = backend.gsettings_get(config.GSETTINGS_MUTTER, "experimental-features")
            try:
                feats = ast.literal_eval(current) if current not in ("@as []", "[]", "") else []
            except (ValueError, SyntaxError):
                feats = []
            if "scale-monitor-framebuffer" in feats:
                feats.remove("scale-monitor-framebuffer")
            ok = backend.run_gsettings(["set", config.GSETTINGS_MUTTER, "experimental-features", str(feats)])
            GLib.idle_add(row.set_undo_done, ok)
            GLib.idle_add(self._log, "✔  Отключено!\n" if ok else "✘  Ошибка\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
        threading.Thread(target=_do, daemon=True).start()


    def _detect_kbd_mode(self):
        value = backend.gsettings_get(config.GSETTINGS_KEYBINDINGS, "switch-input-source")
        is_caps = "Caps" in value
        is_ctrl = "Control" in value
        is_alt = "Alt" in value and "Super" not in value
        is_win = "Super" in value

        config.state_set("setting_kbd_altshift", is_alt)
        config.state_set("setting_kbd_capslock", is_caps)
        config.state_set("setting_kbd_ctrlshift", is_ctrl)
        config.state_set("setting_kbd_winspace", is_win)

        if is_caps:
            config.state_set("setting_kbd_mode", "capslock")
        elif is_ctrl:
            config.state_set("setting_kbd_mode", "ctrlshift")
        elif is_alt:
            config.state_set("setting_kbd_mode", "altshift")
        elif is_win:
            config.state_set("setting_kbd_mode", "winspace")

        GLib.idle_add(self._r_caps._set_ui, is_caps)
        GLib.idle_add(self._r_ctrl._set_ui, is_ctrl)
        GLib.idle_add(self._r_alt._set_ui, is_alt)
        GLib.idle_add(self._r_win._set_ui, is_win)

    def _reset_kbd_bindings(self):
        backend.run_gsettings(["reset", config.GSETTINGS_KEYBINDINGS, "switch-input-source"])
        backend.run_gsettings(["reset", config.GSETTINGS_KEYBINDINGS, "switch-input-source-backward"])

    def _on_altshift(self, row):
        row.set_working()
        self._log("\n▶  Настройка Alt+Shift...\n")

        def _do():
            ok = (
                backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source", "['<Shift>Alt_L']"])
                and backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source-backward", "['<Alt>Shift_L']"])
            )
            if ok:
                config.state_set("setting_kbd_mode", "altshift")
                config.state_set("setting_kbd_capslock", False)
                config.state_set("setting_kbd_ctrlshift", False)
                config.state_set("setting_kbd_winspace", False)
            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._r_caps._set_ui, False)
            GLib.idle_add(self._r_ctrl._set_ui, False)
            GLib.idle_add(self._r_win._set_ui, False)
            GLib.idle_add(self._log, "✔  Alt+Shift готов!\n" if ok else "✘  Ошибка\n")

        threading.Thread(target=_do, daemon=True).start()

    def _on_altshift_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс Alt+Shift...\n")
        def _do():
            self._reset_kbd_bindings()
            config.state_set("setting_kbd_altshift", False)
            GLib.idle_add(row.set_undo_done, True)
            GLib.idle_add(self._log, "✔  Сброшено на Win+Space\n")
            GLib.idle_add(self._r_win._set_ui, True)
            GLib.idle_add(self._r_caps._set_ui, False)
            GLib.idle_add(self._r_ctrl._set_ui, False)
        threading.Thread(target=_do, daemon=True).start()

    def _on_capslock(self, row):
        row.set_working()
        self._log("\n▶  Настройка CapsLock...\n")

        def _do():
            ok = (
                backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source", "['Caps_Lock']"])
                and backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source-backward", "['<Shift>Caps_Lock']"])
            )
            if ok:
                config.state_set("setting_kbd_mode", "capslock")
                config.state_set("setting_kbd_altshift", False)
                config.state_set("setting_kbd_ctrlshift", False)
                config.state_set("setting_kbd_winspace", False)
            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._r_alt._set_ui, False)
            GLib.idle_add(self._r_ctrl._set_ui, False)
            GLib.idle_add(self._r_win._set_ui, False)
            GLib.idle_add(self._log, "✔  CapsLock готов!\n" if ok else "✘  Ошибка\n")

        threading.Thread(target=_do, daemon=True).start()

    def _on_capslock_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс CapsLock...\n")
        def _do():
            self._reset_kbd_bindings()
            config.state_set("setting_kbd_capslock", False)
            GLib.idle_add(row.set_undo_done, True)
            GLib.idle_add(self._log, "✔  Сброшено на Win+Space\n")
            GLib.idle_add(self._r_win._set_ui, True)
            GLib.idle_add(self._r_alt._set_ui, False)
            GLib.idle_add(self._r_ctrl._set_ui, False)
        threading.Thread(target=_do, daemon=True).start()

    def _on_ctrlshift(self, row):
        row.set_working()
        self._log("\n▶  Настройка Ctrl+Shift...\n")

        def _do():
            ok = (
                backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source", "['<Shift>Control_L']"])
                and backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source-backward", "['<Control>Shift_L']"])
            )
            if ok:
                config.state_set("setting_kbd_mode", "ctrlshift")
                config.state_set("setting_kbd_altshift", False)
                config.state_set("setting_kbd_capslock", False)
                config.state_set("setting_kbd_winspace", False)
            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._r_alt._set_ui, False)
            GLib.idle_add(self._r_caps._set_ui, False)
            GLib.idle_add(self._r_win._set_ui, False)
            GLib.idle_add(self._log, "✔  Ctrl+Shift готов!\n" if ok else "✘  Ошибка\n")

        threading.Thread(target=_do, daemon=True).start()

    def _on_ctrlshift_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс Ctrl+Shift...\n")
        def _do():
            self._reset_kbd_bindings()
            config.state_set("setting_kbd_ctrlshift", False)
            GLib.idle_add(row.set_undo_done, True)
            GLib.idle_add(self._log, "✔  Сброшено на Win+Space\n")
            GLib.idle_add(self._r_win._set_ui, True)
            GLib.idle_add(self._r_alt._set_ui, False)
            GLib.idle_add(self._r_caps._set_ui, False)
        threading.Thread(target=_do, daemon=True).start()

    def _on_winspace(self, row):
        row.set_working()
        self._log("\n▶  Настройка Win+Space...\n")

        def _do():
            ok = (
                backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source", "['<Super>space']"])
                and backend.run_gsettings(["set", config.GSETTINGS_KEYBINDINGS, "switch-input-source-backward", "['<Shift><Super>space']"])
            )
            if ok:
                config.state_set("setting_kbd_mode", "winspace")
                config.state_set("setting_kbd_altshift", False)
                config.state_set("setting_kbd_capslock", False)
                config.state_set("setting_kbd_ctrlshift", False)
            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._r_alt._set_ui, False)
            GLib.idle_add(self._r_caps._set_ui, False)
            GLib.idle_add(self._r_ctrl._set_ui, False)
            GLib.idle_add(self._log, "✔  Win+Space готов!\n" if ok else "✘  Ошибка\n")

        threading.Thread(target=_do, daemon=True).start()

    def _on_winspace_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс Win+Space...\n")
        def _do():
            self._reset_kbd_bindings()
            config.state_set("setting_kbd_winspace", False)
            GLib.idle_add(row.set_undo_done, True)
            GLib.idle_add(self._log, "✔  Сброшено на Win+Space\n")
            GLib.idle_add(self._r_win._set_ui, True)
        threading.Thread(target=_do, daemon=True).start()


    _PAPIRUS_COLOR_KEYS = [
        "adwaita", "yaru", "nordic", "breeze", "blue",
        "brown", "cyan", "green", "grey", "indigo",
        "magenta", "orange", "pink", "purple", "red",
        "teal", "violet", "white", "yellow",
    ]

    def _create_papirus_row(self):
        row = Adw.ActionRow()
        row.set_title("Иконки Papirus")
        row.set_subtitle("Пакет papirus-icon-theme — тема подбирается по светлой/тёмной схеме")
        row.add_prefix(make_icon("application-x-addon-symbolic"))

        model = Gtk.StringList.new([k.capitalize() for k in self._PAPIRUS_COLOR_KEYS])
        self._papirus_color_drop = Gtk.DropDown.new(model, None)
        self._papirus_color_drop.set_valign(Gtk.Align.CENTER)
        self._papirus_color_drop.set_visible(False)

        self._papirus_trash_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        self._papirus_trash_btn.add_css_class("destructive-action")
        self._papirus_trash_btn.add_css_class("circular")
        self._papirus_trash_btn.set_valign(Gtk.Align.CENTER)
        self._papirus_trash_btn.connect("clicked", lambda _: self._on_uninstall_papirus())
        self._papirus_trash_btn.set_visible(False)

        self._papirus_btn = make_button("Установить", width=130)
        self._papirus_btn.set_sensitive(False)
        self._papirus_btn.connect("clicked", self._on_papirus_btn_clicked)

        suffix = Gtk.Box(spacing=8)
        suffix.set_valign(Gtk.Align.CENTER)
        suffix.append(self._papirus_color_drop)
        suffix.append(self._papirus_trash_btn)
        suffix.append(self._papirus_btn)
        row.add_suffix(suffix)

        self._papirus_installed = False
        cached_installed = config.state_get("app_papirus_icons") is True
        if cached_installed:
            cached_applied = config.state_get("papirus_applied") is True
            self._set_papirus_ui(cached_installed, cached_applied)
        threading.Thread(target=self._check_papirus, daemon=True).start()
        return row

    def _check_papirus(self):
        installed = backend.check_app_installed({"check": ["rpm", "papirus-icon-theme"]})
        config.state_set("app_papirus_icons", installed)
        applied = False
        if installed:
            icon_theme = backend.gsettings_get("org.gnome.desktop.interface", "icon-theme")
            applied = "Papirus" in icon_theme
            config.state_set("papirus_applied", applied)
        GLib.idle_add(self._set_papirus_ui, installed, applied)

    def _set_papirus_ui(self, installed, applied=False):
        self._papirus_installed = installed
        if installed:
            self._papirus_color_drop.set_visible(True)
            self._papirus_trash_btn.set_visible(True)
            self._papirus_trash_btn.set_sensitive(True)
            if applied:
                self._papirus_btn.set_label("Применено")
                self._papirus_btn.set_sensitive(True)
                self._papirus_btn.remove_css_class("suggested-action")
                self._papirus_btn.add_css_class("flat")
            else:
                self._papirus_btn.set_label("Применить")
                self._papirus_btn.set_sensitive(True)
                self._papirus_btn.remove_css_class("flat")
                self._papirus_btn.add_css_class("suggested-action")
        else:
            self._papirus_color_drop.set_visible(False)
            self._papirus_trash_btn.set_visible(False)
            self._papirus_btn.set_label("Установить")
            self._papirus_btn.set_sensitive(True)
            self._papirus_btn.remove_css_class("flat")
            self._papirus_btn.add_css_class("suggested-action")

    def _on_papirus_btn_clicked(self, _):
        if self._papirus_installed:
            self._on_apply_papirus()
        else:
            self._on_install_papirus()

    def _on_install_papirus(self):
        self._papirus_btn.set_sensitive(False)
        self._papirus_btn.set_label("…")
        self._log("\n▶  Установка papirus-icon-theme...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка иконок Papirus...")

        def _done(ok):
            if ok:
                self._log("✔  Papirus установлен!\n")
                if hasattr(win, "stop_progress"): win.stop_progress(ok)
                GLib.idle_add(self._set_papirus_ui, True)
                GLib.idle_add(self._on_apply_papirus)
            else:
                self._log("✘  Ошибка установки papirus-icon-theme\n")
                if hasattr(win, "stop_progress"): win.stop_progress(ok)
                GLib.idle_add(self._set_papirus_ui, False)
                GLib.idle_add(self._papirus_btn.set_label, "Повторить")

        backend.run_privileged(["dnf", "install", "-y", "papirus-icon-theme"], self._log, _done)

    def _on_uninstall_papirus(self):
        self._papirus_trash_btn.set_sensitive(False)
        self._papirus_btn.set_sensitive(False)
        self._log("\n▶  Удаление papirus-icon-theme...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление иконок Papirus...")

        def _done(ok):
            if ok:
                self._log("✔  Papirus удалён!\n")
                config.state_set("papirus_applied", False)
            else:
                self._log("✘  Ошибка удаления papirus-icon-theme\n")
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
            GLib.idle_add(self._set_papirus_ui, not ok)

        backend.run_privileged(["dnf", "remove", "-y", "papirus-icon-theme"], self._log, _done)

    def _on_apply_papirus(self):
        idx = self._papirus_color_drop.get_selected()
        color = self._PAPIRUS_COLOR_KEYS[idx].capitalize() if idx != Gtk.INVALID_LIST_POSITION else "Adwaita"

        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Применение темы Papirus...")

        def _do():
            scheme = backend.gsettings_get("org.gnome.desktop.interface", "color-scheme")
            dark = "dark" in scheme.lower()
            theme = f"Papirus-{'Dark' if dark else 'Light'}-{color}"
            ok = backend.run_gsettings(["set", "org.gnome.desktop.interface", "icon-theme", theme])
            if ok:
                config.state_set("papirus_applied", True)
                GLib.idle_add(self._set_papirus_ui, True, True)
            GLib.idle_add(self._log, f"✔  Тема {theme} применена!\n" if ok else "✘  Ошибка применения темы Papirus\n")
            if hasattr(win, "stop_progress"): GLib.idle_add(win.stop_progress, ok)

        threading.Thread(target=_do, daemon=True).start()

