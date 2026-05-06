
import os
import shutil
import subprocess
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from core import backend
from ui.rows import SettingRow
from ui.widgets import make_scrolled_page, scroll_child_into_view

_FASTFETCH_CONFIG = r"""{
    "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
    "display": {
		"separator": "\u001b[90m ▐ "
    },
    "modules": [
        {
            "type": "os",
            "key": "",
            "keyColor": "94",
            "format": "{2} {#2}[p11]"
        },
        {
            "type": "kernel",
            "key": "",
            "keyColor": "39"
        },
        {
            "type": "packages",
            "key": "󰏖",
            "keyColor": "33"
        },
        {
            "type": "shell",
            "key": "",
            "keyColor": "94",
            "format": "{1} {#2}[{4}] {#2}"
        },
        {
            "type": "terminal",
            "key": "",
            "keyColor": "39",
            "format": "{1} {#2}[{6}]"
        },
        "break",

        {
            "type": "wm",
            "key": "󱍜",
            "keyColor": "34"
        },
        {
            "type": "wmtheme",
            "key": "󰉼",
            "keyColor": "33"
        },
        {
            "type": "icons",
            "key": "",
            "keyColor": "93"
        },

        "break",
        {
            "type": "host",
            "key": "󰌢",
            "keyColor": "92"
        },
        {
            "type": "display",
            "key": "󰹑",
            "keyColor": "32"
        },
        {
            "type": "cpu",
            "key": "󰍛",
            "keyColor": "96"
        },
        {
            "type": "gpu",
            "key": "󰢮",
            "keyColor": "96"
        },
        {
            "type": "memory",
            "key": "",
            "keyColor": "36"
        },
        {
            "type": "disk",
            "key": "󰋊",
            // "format": "{size-used} / {size-total} ({size-percentage})"
        },

        "break",
        {
            "type": "uptime",
            "key": "󱤦",
            "keyColor": "39"
        },
        {
            "type": "command",
            "key": "󱦟",
            "keyColor": "31",
            "text": "birth_install=$(stat -c %W /); current=$(date +%s); time_progression=$((current - birth_install)); days_difference=$((time_progression / 86400)); echo $days_difference день",
            "format": "Этой системе {1}"
        },

        "break",
        {
            "type": "poweradapter",
            "key": "{#90}{$1}│ {#91}Power       {#90}│",
            "format": "{$2}{$3}{name}",
            // fastfetch -h poweradapter-format
            // {2}: PowerAdapter name - name
            // The default is something similar to "{1}W".
        },
        {
            "type": "battery",
            "key": "Battery",
            "temp": true,
        },

        "break",
        "colors"
    ]
}
"""

class TerminalPage(Gtk.Box):
    def __init__(self, log_fn):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._log = log_fn
        scroll, body = make_scrolled_page()
        self._body = body
        self.append(scroll)

        self._build_ghostty_group(body)
        self._build_shortcuts_group(body)
        self._build_zsh_group(body)
        self._build_fastfetch_group(body)
        self._register_terminal_search_rows()

    def _register_terminal_search_rows(self):
        self._terminal_row_by_id = {
            "ghostty_install": self._row_ghostty_install,
            "shortcut_1": self._row_shortcut_1,
            "shortcut_2": self._row_shortcut_2,
            "zsh_install": self._row_zsh_install,
            "zsh_default": self._row_zsh_default,
            "fastfetch_install": self._row_fastfetch_install,
            "firacode_install": self._row_font_install,
            "font_apply": self._row_font_apply,
            "ffcfg_install": self._row_ff_config,
        }

    def focus_row_by_id(self, row_id: str) -> bool:
        w = self._terminal_row_by_id.get(row_id)
        if w is None:
            return False
        scroll = self.get_first_child()
        if isinstance(scroll, Gtk.ScrolledWindow):
            scroll_child_into_view(scroll, w)
        GLib.idle_add(w.grab_focus)
        return True

    def _build_ghostty_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("Ghostty")
        group.set_description("Современный GPU-ускоренный терминал из COPR (scottames/ghostty)")

        btn_all = Gtk.Button(label="Применить всё")
        btn_all.set_valign(Gtk.Align.CENTER)
        btn_all.add_css_class("suggested-action")
        btn_all.connect("clicked", self._on_apply_all)
        group.set_header_suffix(btn_all)

        body.append(group)

        self._row_ghostty_install = SettingRow(
            "utilities-terminal-symbolic", "Установить Ghostty",
            "dnf copr enable scottames/ghostty &amp;&amp; dnf install ghostty", "Установить",
            self._on_install_ghostty,
            lambda: backend.check_app_installed({"check": ["which", "ghostty"]}),
            "term_ghostty_install", "Установлен",
            self._on_remove_ghostty, "Удалить", "user-trash-symbolic"
        )
        group.add(self._row_ghostty_install)

    def _on_install_ghostty(self, row):
        row.set_working()
        self._log("\n▶  Установка Ghostty...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка Ghostty...")
        def _done(ok):
            row.set_done(ok)
            if hasattr(win, "stop_progress"): win.stop_progress(ok)
        backend.run_privileged(["bash", "-c", "dnf copr enable scottames/ghostty -y && dnf install -y ghostty"], self._log, _done)

    def _on_remove_ghostty(self, row):
        row.set_working()
        self._log("\n▶  Удаление Ghostty...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление Ghostty...")
        backend.run_privileged(["dnf", "remove", "-y", "ghostty"], self._log,
            lambda ok: (row.set_undo_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))


    def _build_shortcuts_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("Горячие клавиши")
        group.set_description("Шорткаты для открытия терминала")
        body.append(group)

        self._row_shortcut_1 = SettingRow(
            "input-keyboard-symbolic", "Terminal 1",
            "Ctrl + Alt + T", "Назначить",
            lambda r: self._set_shortcut(r, "custom0", "Terminal", "ghostty", "<Control><Alt>t", "<Primary><Alt>t"),
            lambda: self._check_shortcut("custom0", "<Control><Alt>t"),
            "term_shortcut_1", "Назначен",
            lambda r: self._remove_shortcut(r, "custom0"), "Сбросить"
        )
        group.add(self._row_shortcut_1)

        self._row_shortcut_2 = SettingRow(
            "input-keyboard-symbolic", "Terminal 2",
            "Super + Enter", "Назначить",
            lambda r: self._set_shortcut(r, "custom1", "Terminal Super", "ghostty", "<Super>Return"),
            lambda: self._check_shortcut("custom1", "<Super>Return"),
            "term_shortcut_2", "Назначен",
            lambda r: self._remove_shortcut(r, "custom1"), "Сбросить"
        )
        group.add(self._row_shortcut_2)

    def _get_custom_bindings(self):
        val = backend.gsettings_get("org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings")
        if not val or val == "@as []":
            return []
        val = val.strip("[]")
        if not val:
            return []
        return [x.strip(" '\"") for x in val.split(",") if x.strip(" '\"")]

    def _check_shortcut(self, uid, binding):
        current_paths = self._get_custom_bindings()
        for path in current_paths:
            if not path.endswith("/"):
                path += "/"
            val = backend.gsettings_get("org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:" + path, "binding")
            if binding in val:
                return True
        return False

    def _set_shortcut(self, row, uid, name, cmd, binding, alt_binding=None):
        row.set_working()
        self._log(f"\n▶  Настройка шортката {name}...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress(f"Настройка шортката {name}...")
        def _do():
            path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/{uid}/"
            schema = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:" + path

            backend.run_gsettings(["set", schema, "name", f"'{name}'"])
            backend.run_gsettings(["set", schema, "command", f"'{cmd}'"])
            backend.run_gsettings(["set", schema, "binding", f"'{binding}'"])

            current = self._get_custom_bindings()
            if path not in current:
                current.append(path)
                array_str = "[" + ", ".join(f"'{p}'" for p in current) + "]"
                backend.run_gsettings(["set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", array_str])

            GLib.idle_add(row.set_done, True)
            GLib.idle_add(self._log, "✔  Шорткат назначен\n")
            if hasattr(win, "stop_progress"): win.stop_progress(True)
        threading.Thread(target=_do, daemon=True).start()

    def _remove_shortcut(self, row, uid):
        row.set_working()
        self._log("\n▶  Удаление шортката...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление шортката...")
        def _do():
            path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/{uid}/"
            current = self._get_custom_bindings()
            if path in current:
                current.remove(path)
                array_str = "[" + ", ".join(f"'{p}'" for p in current) + "]"
                backend.run_gsettings(["set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", array_str])

            schema = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:" + path
            backend.run_gsettings(["reset", schema, "name"])
            backend.run_gsettings(["reset", schema, "command"])
            backend.run_gsettings(["reset", schema, "binding"])

            GLib.idle_add(row.set_undo_done, True)
            GLib.idle_add(self._log, "✔  Шорткат удалён\n")
            if hasattr(win, "stop_progress"): win.stop_progress(True)
        threading.Thread(target=_do, daemon=True).start()


    def _build_zsh_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("ZSH")
        group.set_description("Устанавливает zsh + git, делает ZSH shell по умолчанию")
        body.append(group)

        self._row_zsh_install = SettingRow(
            "utilities-terminal-symbolic", "Установить git и zsh",
            "dnf install -y git zsh", "Установить",
            self._on_install_zsh,
            lambda: backend.check_app_installed({"check": ["which", "zsh"]}),
            "term_zsh_install", "Установлен",
            self._on_remove_zsh, "Удалить", "user-trash-symbolic"
        )
        group.add(self._row_zsh_install)

        self._row_zsh_default = SettingRow(
            "system-run-symbolic", "ZSH по умолчанию",
            "chsh -s /bin/zsh", "Применить",
            self._on_zsh_default,
            self._check_zsh_default,
            "term_zsh_default", "Применено",
            self._on_zsh_default_undo, "Сбросить"
        )
        group.add(self._row_zsh_default)

    def _on_install_zsh(self, row):
        row.set_working()
        self._log("\n▶  Установка git и zsh...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка ZSH...")
        backend.run_privileged(["dnf", "install", "-y", "git", "zsh"], self._log,
            lambda ok: (row.set_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _on_remove_zsh(self, row):
        row.set_working()
        self._log("\n▶  Удаление zsh...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление ZSH...")
        backend.run_privileged(["dnf", "remove", "-y", "zsh"], self._log,
            lambda ok: (row.set_undo_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _check_zsh_default(self):
        return os.environ.get("SHELL") == "/bin/zsh"

    def _on_zsh_default(self, row):
        row.set_working()
        self._log("\n▶  Установка ZSH по умолчанию...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка ZSH по умолчанию...")
        user = os.environ.get("USER")
        backend.run_privileged(["chsh", "-s", "/bin/zsh", user], self._log,
            lambda ok: (row.set_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _on_zsh_default_undo(self, row):
        row.set_working()
        self._log("\n▶  Возврат Bash по умолчанию...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Возврат Bash по умолчанию...")
        user = os.environ.get("USER")
        backend.run_privileged(["chsh", "-s", "/bin/bash", user], self._log,
            lambda ok: (row.set_undo_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))


    def _build_fastfetch_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("Fastfetch + шрифты")
        group.set_description("Системная информация с иконками Nerd Fonts")
        body.append(group)

        self._row_fastfetch_install = SettingRow(
            "dialog-information-symbolic", "Установить Fastfetch",
            "dnf install fastfetch", "Установить",
            self._on_install_fastfetch,
            lambda: backend.check_app_installed({"check": ["which", "fastfetch"]}),
            "term_ff_install", "Установлен",
            self._on_remove_fastfetch, "Удалить", "user-trash-symbolic"
        )
        group.add(self._row_fastfetch_install)

        self._row_font_install = SettingRow(
            "font-x-generic-symbolic", "Шрифт FiraCode Nerd Font",
            "dnf install fira-code-fonts", "Установить",
            self._on_install_font,
            lambda: backend.check_app_installed({"check": ["rpm", "fira-code-fonts"]}),
            "term_font_install", "Установлен",
            self._on_remove_font, "Удалить", "user-trash-symbolic"
        )
        group.add(self._row_font_install)

        self._row_font_apply = SettingRow(
            "font-x-generic-symbolic", "Применить шрифт в Ghostty",
            "FiraCode Nerd Font Regular 14", "Применить",
            self._on_apply_font,
            self._check_ghostty_font,
            "term_font_apply", "Применён",
            self._on_apply_font_undo, "Сбросить"
        )
        group.add(self._row_font_apply)

        self._row_ff_config = SettingRow(
            "document-save-symbolic", "Конфиг Fastfetch (Default)",
            "Сохраняет в ~/.config/fastfetch/config.jsonc", "Установить",
            self._on_install_ff_config,
            lambda: backend.check_app_installed({"check": ["path", "~/.config/fastfetch/config.jsonc"]}),
            "term_ff_config", "Установлен",
            self._on_remove_ff_config, "Удалить", "user-trash-symbolic"
        )
        group.add(self._row_ff_config)

    def _on_install_fastfetch(self, row):
        row.set_working()
        self._log("\n▶  Установка Fastfetch...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка Fastfetch...")
        backend.run_privileged(["dnf", "install", "-y", "fastfetch"], self._log,
            lambda ok: (row.set_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _on_remove_fastfetch(self, row):
        row.set_working()
        self._log("\n▶  Удаление Fastfetch...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление Fastfetch...")
        backend.run_privileged(["dnf", "remove", "-y", "fastfetch"], self._log,
            lambda ok: (row.set_undo_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _on_install_font(self, row):
        row.set_working()
        self._log("\n▶  Установка шрифта...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Установка шрифта...")
        backend.run_privileged(["dnf", "install", "-y", "fira-code-fonts"], self._log,
            lambda ok: (row.set_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _on_remove_font(self, row):
        row.set_working()
        self._log("\n▶  Удаление шрифта...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление шрифта...")
        backend.run_privileged(["dnf", "remove", "-y", "fira-code-fonts"], self._log,
            lambda ok: (row.set_undo_done(ok), win.stop_progress(ok) if hasattr(win, "stop_progress") else None))

    def _check_ghostty_font(self):
        try:
            p = Path(os.path.expanduser("~/.config/ghostty/config"))
            return "font-family = FiraCode Nerd Font" in p.read_text()
        except Exception:
            return False

    def _on_apply_font(self, row):
        row.set_working()
        self._log("\n▶  Применение шрифта в Ghostty...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Применение шрифта...")
        def _do():
            p = Path(os.path.expanduser("~/.config/ghostty/config"))
            p.parent.mkdir(parents=True, exist_ok=True)
            existing = p.read_text() if p.exists() else ""
            lines = existing.splitlines()
            new_lines = []
            has_family = False
            has_size = False
            for line in lines:
                if line.strip().startswith("font-family"):
                    new_lines.append("font-family = FiraCode Nerd Font")
                    has_family = True
                elif line.strip().startswith("font-size"):
                    new_lines.append("font-size = 14")
                    has_size = True
                else:
                    new_lines.append(line)
            if not has_family:
                new_lines.append("font-family = FiraCode Nerd Font")
            if not has_size:
                new_lines.append("font-size = 14")
            p.write_text("\n".join(new_lines).strip() + "\n")
            GLib.idle_add(row.set_done, True)
            GLib.idle_add(self._log, "✔  Шрифт применён\n")
            if hasattr(win, "stop_progress"): win.stop_progress(True)
        threading.Thread(target=_do, daemon=True).start()

    def _on_apply_font_undo(self, row):
        row.set_working()
        self._log("\n▶  Сброс шрифта в Ghostty...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Сброс шрифта...")
        def _do():
            p = Path(os.path.expanduser("~/.config/ghostty/config"))
            if p.exists():
                existing = p.read_text()
                lines = existing.splitlines()
                new_lines = [line for line in lines if not line.strip().startswith("font-family") and not line.strip().startswith("font-size")]
                if len(new_lines) == 0 and existing.strip():
                    new_lines = []
                p.write_text("\n".join(new_lines).strip() + "\n" if new_lines else "")
            GLib.idle_add(row.set_undo_done, True)
            GLib.idle_add(self._log, "✔  Шрифт сброшен\n")
            if hasattr(win, "stop_progress"): win.stop_progress(True)
        threading.Thread(target=_do, daemon=True).start()

    def _on_install_ff_config(self, row):
        row.set_working()
        self._log("\n▶  Создание конфига Fastfetch...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Создание конфига Fastfetch...")
        def _do():
            p = Path(os.path.expanduser("~/.config/fastfetch/config.jsonc"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(_FASTFETCH_CONFIG, encoding="utf-8")
            GLib.idle_add(row.set_done, True)
            GLib.idle_add(self._log, "✔  Конфиг создан\n")
            if hasattr(win, "stop_progress"): win.stop_progress(True)
        threading.Thread(target=_do, daemon=True).start()

    def _on_remove_ff_config(self, row):
        row.set_working()
        self._log("\n▶  Удаление конфига Fastfetch...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Удаление конфига Fastfetch...")
        def _do():
            p = Path(os.path.expanduser("~/.config/fastfetch/config.jsonc"))
            if p.exists():
                p.unlink()
            GLib.idle_add(row.set_undo_done, True)
            GLib.idle_add(self._log, "✔  Конфиг удалён\n")
            if hasattr(win, "stop_progress"): win.stop_progress(True)
        threading.Thread(target=_do, daemon=True).start()


    def _on_apply_all(self, btn):
        btn.set_sensitive(False)
        self._log("\n▶  Применение всех настроек терминала...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"): win.start_progress("Настройка терминала...")
        threading.Thread(target=self._do_apply_all, args=(btn,), daemon=True).start()

    def _do_apply_all(self, btn):
        def run_step(row, action_name, sync_fn):
            try:
                if row._check_fn and row._check_fn():
                    GLib.idle_add(row.set_done, True)
                    return True
            except Exception:
                pass

            GLib.idle_add(row.set_working)
            GLib.idle_add(self._log, f"▶  {action_name}...\n")

            try:
                ok = sync_fn()
            except Exception as e:
                GLib.idle_add(self._log, f"✘  Ошибка: {e}\n")
                ok = False

            GLib.idle_add(row.set_done, ok)
            GLib.idle_add(self._log, f"{'✔' if ok else '✘'}  {action_name}\n")
            return ok

        run_step(self._row_ghostty_install, "Установка Ghostty",
            lambda: backend.run_privileged_sync(["bash", "-c", "dnf copr enable scottames/ghostty -y && dnf install -y ghostty"], self._log))

        def _sync_shortcut(uid, name, cmd, binding):
            path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/{uid}/"
            schema = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:" + path
            backend.run_gsettings(["set", schema, "name", f"'{name}'"])
            backend.run_gsettings(["set", schema, "command", f"'{cmd}'"])
            backend.run_gsettings(["set", schema, "binding", f"'{binding}'"])
            current = self._get_custom_bindings()
            if path not in current:
                current.append(path)
                array_str = "[" + ", ".join(f"'{p}'" for p in current) + "]"
                backend.run_gsettings(["set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", array_str])
            return True

        def _sync_ghostty_font():
            p = Path(os.path.expanduser("~/.config/ghostty/config"))
            p.parent.mkdir(parents=True, exist_ok=True)
            existing = p.read_text() if p.exists() else ""
            lines = existing.splitlines()
            new_lines = []
            has_family = False
            has_size = False
            for line in lines:
                if line.strip().startswith("font-family"):
                    new_lines.append("font-family = FiraCode Nerd Font")
                    has_family = True
                elif line.strip().startswith("font-size"):
                    new_lines.append("font-size = 14")
                    has_size = True
                else:
                    new_lines.append(line)
            if not has_family:
                new_lines.append("font-family = FiraCode Nerd Font")
            if not has_size:
                new_lines.append("font-size = 14")
            p.write_text("\n".join(new_lines).strip() + "\n")
            return True

        run_step(self._row_shortcut_1, "Шорткат Terminal 1",
            lambda: _sync_shortcut("custom0", "Terminal", "ghostty", "<Control><Alt>t"))

        run_step(self._row_shortcut_2, "Шорткат Terminal 2",
            lambda: _sync_shortcut("custom1", "Terminal Super", "ghostty", "<Super>Return"))

        run_step(self._row_zsh_install, "Установка ZSH",
            lambda: backend.run_privileged_sync(["dnf", "install", "-y", "git", "zsh"], self._log))

        run_step(self._row_zsh_default, "ZSH по умолчанию",
            lambda: backend.run_privileged_sync(["chsh", "-s", "/bin/zsh", os.environ.get("USER")], self._log))

        run_step(self._row_fastfetch_install, "Установка Fastfetch",
            lambda: backend.run_privileged_sync(["dnf", "install", "-y", "fastfetch"], self._log))

        run_step(self._row_font_install, "Установка шрифта",
            lambda: backend.run_privileged_sync(["dnf", "install", "-y", "fira-code-fonts"], self._log))

        run_step(self._row_font_apply, "Применение шрифта",
            lambda: _sync_ghostty_font())

        def _sync_ff_config():
            p = Path(os.path.expanduser("~/.config/fastfetch/config.jsonc"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(_FASTFETCH_CONFIG, encoding="utf-8")
            return True
        run_step(self._row_ff_config, "Конфиг Fastfetch", _sync_ff_config)

        GLib.idle_add(btn.set_sensitive, True)
        GLib.idle_add(self._log, "\n✔  Все настройки терминала применены!\n")
        win = self.get_root()
        if hasattr(win, "stop_progress"): GLib.idle_add(win.stop_progress, True)
