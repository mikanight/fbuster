"""Проверка поддержки sched_ext в текущем (загруженном) ядре."""

from __future__ import annotations

import os

SYSFS_SCHED_EXT = "/sys/kernel/sched_ext"

# Пакет ядра для установки через dnf: подтягивает актуальную сборку выбранной
# линии в репозиториях Fedora.
KERNEL_IMAGE_SCHED_EXT = "kernel"


def has_sched_ext() -> bool:
    return os.path.exists(SYSFS_SCHED_EXT)
