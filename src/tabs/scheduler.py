import os
import shutil
import subprocess
import tempfile
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from core import backend
from ui.rows import SettingRow
from ui.widgets import make_scrolled_page, scroll_child_into_view

_ZORKIY_REPO = "https://github.com/Toxblh/gnome-shell-extension-zorkiy.git"
_ZORKIY_UUID = "zorkiy@toxblh.ru"
_ZORKIY_DIR = os.path.expanduser("~/.local/share/gnome-shell/extensions/" + _ZORKIY_UUID)


def _check_zorkiy():
    return os.path.isdir(_ZORKIY_DIR)


class SchedulerPage(Gtk.Box):
    def __init__(self, log_fn):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._log = log_fn
        scroll, body = make_scrolled_page()
        self._body = body
        self.append(scroll)

        self._build_s76_group(body)
        self._build_zorkiy_group(body)
        self._register_search_rows()

    def _register_search_rows(self):
        self._rows = {
            "s76_install": self._row_s76_install,
            "s76_service": self._row_s76_service,
            "zorkiy_install": self._row_zorkiy,
        }

    def focus_row_by_id(self, row_id: str) -> bool:
        w = self._rows.get(row_id)
        if w is None:
            return False
        scroll = self.get_first_child()
        if isinstance(scroll, Gtk.ScrolledWindow):
            scroll_child_into_view(scroll, w)
        GLib.idle_add(w.grab_focus)
        return True

    def _build_s76_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("System76 Scheduler")
        group.set_description(
            "Служба из Pop!_OS (System76): подстраивает латентности CFS, "
            "назначает nice и I/O-приоритеты по правилам KDL, отслеживает PipeWire. "
            "Установка из COPR kylegospo/system76-scheduler."
        )
        body.append(group)

        self._row_s76_install = SettingRow(
            "application-x-executable-symbolic",
            "Установить System76 Scheduler",
            "dnf copr enable kylegospo/system76-scheduler &amp;&amp; dnf install system76-scheduler",
            "Установить",
            self._on_install_s76,
            lambda: shutil.which("system76-scheduler") is not None,
            "s76_installed",
            "Установлен",
            self._on_uninstall_s76,
            "Удалить",
            "user-trash-symbolic",
        )
        group.add(self._row_s76_install)

        self._row_s76_service = SettingRow(
            "system-run-symbolic",
            "Включить службу",
            "systemctl enable --now system76-scheduler",
            "Включить",
            self._on_enable_s76,
            self._check_s76_service,
            "s76_service_enabled",
            "Активна",
            self._on_disable_s76,
            "Отключить",
            "media-playback-pause-symbolic",
        )
        group.add(self._row_s76_service)

    def _build_zorkiy_group(self, body):
        group = Adw.PreferencesGroup()
        group.set_title("Zorkiy — расширение GNOME")
        group.set_description(
            "Отслеживает фокусное окно через Mutter и передаёт app-id "
            "в system76-scheduler для умной CPU-приоритизации. "
            "Лёгкая замена трекингу pop-shell."
        )
        body.append(group)

        self._row_zorkiy = SettingRow(
            "application-x-addon-symbolic",
            "Установить Zorkiy",
            "git clone &amp;&amp; gnome-extensions enable zorkiy@toxblh.ru",
            "Установить",
            self._on_install_zorkiy,
            _check_zorkiy,
            "zorkiy_installed",
            "Установлен",
            self._on_uninstall_zorkiy,
            "Удалить",
            "user-trash-symbolic",
        )
        group.add(self._row_zorkiy)

    # --- System76 Scheduler (COPR) ---

    def _on_install_s76(self, row):
        row.set_working()
        self._log("\n▶  Установка System76 Scheduler из COPR...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"):
            win.start_progress("Установка System76 Scheduler...")

        cmd = [
            "bash", "-c",
            "dnf copr enable kylegospo/system76-scheduler -y && "
            "dnf install system76-scheduler -y"
        ]

        def _done(ok):
            row.set_done(ok)
            if ok:
                self._log("✔  System76 Scheduler установлен.\n")
                GLib.idle_add(self._row_s76_service._refresh)
            else:
                self._log("✘  Ошибка установки System76 Scheduler.\n")
            if hasattr(win, "stop_progress"):
                win.stop_progress(ok)

        backend.run_privileged(cmd, self._log, _done)

    def _on_uninstall_s76(self, row):
        row.set_working()
        self._log("\n▶  Удаление System76 Scheduler...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"):
            win.start_progress("Удаление System76 Scheduler...")

        cmd = [
            "bash", "-c",
            "systemctl disable --now system76-scheduler 2>/dev/null || true; "
            "dnf remove system76-scheduler -y"
        ]

        def _done(ok):
            row.set_undo_done(ok)
            self._log("✔  System76 Scheduler удалён.\n" if ok else "✘  Ошибка удаления.\n")
            if hasattr(win, "stop_progress"):
                win.stop_progress(ok)

        backend.run_privileged(cmd, self._log, _done)

    def _check_s76_service(self):
        try:
            r = subprocess.run(
                ["systemctl", "is-enabled", "system76-scheduler"],
                capture_output=True, text=True, timeout=5,
            )
            return r.returncode == 0 and r.stdout.strip() in ("enabled", "static")
        except OSError:
            return False

    def _on_enable_s76(self, row):
        row.set_working()
        self._log("\n▶  Включение system76-scheduler...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"):
            win.start_progress("Включение System76 Scheduler...")

        def _done(ok):
            row.set_done(ok)
            self._log("✔  Служба запущена.\n" if ok else "✘  Ошибка запуска.\n")
            if hasattr(win, "stop_progress"):
                win.stop_progress(ok)

        backend.run_privileged(
            ["bash", "-c", "systemctl daemon-reload && systemctl enable --now system76-scheduler"],
            self._log, _done,
        )

    def _on_disable_s76(self, row):
        row.set_working()
        self._log("\n▶  Отключение system76-scheduler...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"):
            win.start_progress("Отключение System76 Scheduler...")

        def _done(ok):
            row.set_undo_done(ok)
            self._log("✔  Служба остановлена.\n" if ok else "✘  Ошибка отключения.\n")
            if hasattr(win, "stop_progress"):
                win.stop_progress(ok)

        backend.run_privileged(
            ["systemctl", "disable", "--now", "system76-scheduler"],
            self._log, _done,
        )

    # --- Zorkiy ---

    def _on_install_zorkiy(self, row):
        row.set_working()
        self._log("\n▶  Установка расширения Zorkiy...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"):
            win.start_progress("Установка Zorkiy...")

        def _thread():
            ok = True
            with tempfile.TemporaryDirectory() as tmpdir:
                r = subprocess.run(
                    ["git", "clone", _ZORKIY_REPO, tmpdir],
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode != 0:
                    self._log(f"✘  git clone ошибка: {r.stderr}\n")
                    GLib.idle_add(row.set_done, False)
                    if hasattr(win, "stop_progress"):
                        GLib.idle_add(win.stop_progress, False)
                    return

                src = os.path.join(tmpdir, _ZORKIY_UUID)
                if not os.path.isdir(src):
                    self._log("✘  Директория расширения не найдена в репозитории.\n")
                    GLib.idle_add(row.set_done, False)
                    if hasattr(win, "stop_progress"):
                        GLib.idle_add(win.stop_progress, False)
                    return

                os.makedirs(_ZORKIY_DIR, exist_ok=True)
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(_ZORKIY_DIR, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

            r = subprocess.run(
                ["gnome-extensions", "enable", _ZORKIY_UUID],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode != 0:
                self._log(f"⚠  Не удалось включить расширение: {r.stderr}\n")
                self._log("Включите вручную: gnome-extensions enable " + _ZORKIY_UUID + "\n")
                self._log("На Wayland потребуется перезайти в сеанс.\n")
                ok = False

            GLib.idle_add(self._finish_zorkiy, row, ok, win)

        threading.Thread(target=_thread, daemon=True).start()

    def _finish_zorkiy(self, row, ok, win):
        if ok:
            row.set_done(True)
            self._log("✔  Zorkiy установлен.\n")
        else:
            row.set_done(False)
            self._log("⚠  Zorkiy установлен, но нужен перезаход.\n")
        if hasattr(win, "stop_progress"):
            win.stop_progress(ok)

    def _on_uninstall_zorkiy(self, row):
        row.set_working()
        self._log("\n▶  Удаление расширения Zorkiy...\n")
        win = self.get_root()
        if hasattr(win, "start_progress"):
            win.start_progress("Удаление Zorkiy...")

        def _thread():
            r = subprocess.run(
                ["gnome-extensions", "disable", _ZORKIY_UUID],
                capture_output=True, text=True, timeout=10,
            )
            if os.path.isdir(_ZORKIY_DIR):
                shutil.rmtree(_ZORKIY_DIR)
            ok = not os.path.isdir(_ZORKIY_DIR)
            GLib.idle_add(self._finish_uninstall_zorkiy, row, ok, win)

        threading.Thread(target=_thread, daemon=True).start()

    def _finish_uninstall_zorkiy(self, row, ok, win):
        row.set_undo_done(ok)
        self._log("✔  Zorkiy удалён.\n" if ok else "✘  Ошибка удаления Zorkiy.\n")
        if hasattr(win, "stop_progress"):
            win.stop_progress(ok)
