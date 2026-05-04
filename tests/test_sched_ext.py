"""Тесты core/sched_ext.py — Фаза 1."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import sched_ext


class TestSchedExtConst:
    def test_kernel_package_is_kernel(self):
        assert sched_ext.KERNEL_IMAGE_SCHED_EXT == "kernel"

    def test_sysfs_path_unchanged(self):
        assert sched_ext.SYSFS_SCHED_EXT == "/sys/kernel/sched_ext"
