"""Тесты core/config.py — Фаза 1."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import config


def test_dnf_lock_files():
    assert config.DNF_LOCK_FILES == ["/var/run/dnf.pid"]


def test_apt_lock_files_removed():
    assert not hasattr(config, "APT_LOCK_FILES")
