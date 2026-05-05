
import os

from core import backend
from ui.common import load_module
from ui.dynamic_page import DynamicPage


class AmdPage(DynamicPage):
    def __init__(self, log_fn):
        super().__init__(load_module("amd"), log_fn)
        self._log = log_fn

    def check_wheel(self):
        try:
            import grp
            user = os.environ.get("USER")
            groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
            gid = os.getgid()
            groups.append(grp.getgrgid(gid).gr_name)
            return "wheel" in groups
        except Exception:
            return False

    def setup_lact_wheel(self):
        user = os.environ.get("USER")
        if not user: return
        self._log(f"\n▶  Добавление пользователя {user} в группу wheel...\n")
        backend.run_privileged(
            ["usermod", "-aG", "wheel", user],
            self._log,
            lambda ok: self._log("✔  Готово! Перезайдите в систему.\n" if ok else "✘  Ошибка\n")
        )

    def apply_lact_config(self, file_path):
        self._log(f"\n▶  Применение конфига LACT: {file_path}...\n")
        backend.run_privileged(
            ["cp", file_path, "/etc/lact/config.yaml"],
            self._log,
            lambda ok: self._restart_lact(ok)
        )

    def _restart_lact(self, ok):
        if not ok:
            self._log("✘  Ошибка копирования конфига.\n")
            return
        self._log("▶  Перезапуск службы lactd...\n")
        backend.run_privileged(
            ["systemctl", "restart", "lactd"],
            self._log,
            lambda ok2: self._log("✔  Конфиг применён!\n" if ok2 else "✘  Ошибка перезапуска lactd\n")
        )


