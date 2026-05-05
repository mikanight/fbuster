
from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any

from core import backend, config


def check_wheel(_page: Any, _arg: Any) -> bool:
    username = os.environ.get("SUDO_USER") or os.environ.get("USER", "")
    r = subprocess.run(["id", "-nG", username], capture_output=True, text=True)
    return "wheel" in r.stdout.split()


def setup_lact_wheel(page, _arg: Any) -> bool:
    username = os.environ.get("SUDO_USER") or os.environ.get("USER", "")
    if not username:
        if page:
            page.log("\n✘  Не удалось определить пользователя\n")
        return False
    cmd = [
        "bash", "-c",
        f"usermod -aG wheel {shlex.quote(username)} && "
        "sed -i 's|\"admin_group\":.*|\"admin_group\": \"wheel\",|' /etc/lact/config.json 2>/dev/null || true",
    ]
    log_fn = page.log if page else lambda _: None
    ok = backend.run_privileged_sync(cmd, log_fn)
    if page:
        page.log("\n✔  Для применения нужно перезайти в сессию\n" if ok else "\n✘  Ошибка\n")
    return ok


def apply_lact_config(page, src_path: str) -> bool:
    if not src_path or not os.path.exists(src_path):
        if page:
            page.log("\n✘  Файл не найден\n")
        return False
    cmd = [
        "bash", "-c",
        f"mkdir -p /etc/lact && cp {shlex.quote(src_path)} /etc/lact/config.json && "
        "systemctl restart lactd 2>/dev/null || true",
    ]
    log_fn = page.log if page else lambda _: None
    ok = backend.run_privileged_sync(cmd, log_fn)
    if ok:
        config.state_set("lact_applied_conf", src_path)
    if page:
        page.log(f"\n✔  Конфиг применён: {os.path.basename(src_path)}\n" if ok else "\n✘  Ошибка\n")
    return ok



