"""Тесты core/checks.py — Фаза 1."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import checks


class TestIsSudoEnabled:
    def test_wheel_group_detected(self):
        mock_result = MagicMock()
        mock_result.stdout = "root wheel adm"
        with patch("subprocess.run", return_value=mock_result):
            assert checks.is_sudo_enabled() is True

    def test_no_wheel_group(self):
        mock_result = MagicMock()
        mock_result.stdout = "users"
        with patch("subprocess.run", return_value=mock_result):
            assert checks.is_sudo_enabled() is False

    def test_subprocess_error_returns_false(self):
        with patch("subprocess.run", side_effect=OSError):
            assert checks.is_sudo_enabled() is False


class TestIsSystemBusy:
    def test_packagekitd_running(self):
        mock_pgrep = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_pgrep):
            assert checks.is_system_busy() is True

    def test_dnf_lock_held(self):
        def run_side_effect(*args, **kwargs):
            if args[0][0] == "pgrep":
                return MagicMock(returncode=1)
            if args[0][0] == "fuser":
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        with (
            patch("os.path.exists", return_value=True),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            assert checks.is_system_busy() is True

    def test_nothing_busy(self):
        def run_side_effect(*args, **kwargs):
            return MagicMock(returncode=1)

        with (
            patch("os.path.exists", return_value=True),
            patch("subprocess.run", side_effect=run_side_effect),
        ):
            assert checks.is_system_busy() is False



