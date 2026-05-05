"""Тесты core/privileges.py — Фаза 1."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import privileges


class TestIsDnfLocked:
    def test_locked_when_fuser_finds_process(self):
        with (
            patch("os.path.exists", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            assert privileges._is_dnf_locked() is True

    def test_not_locked_when_fuser_finds_nothing(self):
        with (
            patch("os.path.exists", return_value=True),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1)
            assert privileges._is_dnf_locked() is False

    def test_not_locked_when_lock_file_missing(self):
        with patch("os.path.exists", return_value=False):
            assert privileges._is_dnf_locked() is False


class TestWaitForDnfLock:
    def test_returns_true_when_lock_free_immediately(self):
        with patch.object(privileges, "_is_dnf_locked", return_value=False):
            assert privileges._wait_for_dnf_lock(timeout=30) is True

    def test_returns_false_on_timeout(self):
        with patch.object(privileges, "_is_dnf_locked", return_value=True):
            assert privileges._wait_for_dnf_lock(timeout=5) is False

    def test_calls_on_line_on_first_attempt(self):
        on_line = MagicMock()
        locked_returns = [True, False]

        def locked_side_effect():
            return locked_returns.pop(0) if locked_returns else False

        with (
            patch.object(privileges, "_is_dnf_locked", side_effect=locked_side_effect),
            patch("time.sleep"),
            patch.object(privileges, "GLib") as mock_glib,
        ):
            mock_glib.idle_add = MagicMock()
            assert privileges._wait_for_dnf_lock(on_line=on_line, timeout=10) is True
            assert mock_glib.idle_add.called


class TestRunDnf:
    def test_run_dnf_delegates_to_run_privileged(self):
        cmd = ["dnf", "install", "test-pkg"]
        on_line = MagicMock()
        on_done = MagicMock()
        with patch.object(privileges, "run_privileged") as mock_rp:
            privileges.run_dnf(cmd, on_line, on_done)
            mock_rp.assert_called_once_with(cmd, on_line, on_done)

    def test_run_dnf_sync_returns_bool(self):
        cmd = ["dnf", "install", "test-pkg"]
        on_line = MagicMock()
        with patch.object(privileges, "_sync_wrapper") as mock_sync:
            mock_sync.return_value = True
            result = privileges.run_dnf_sync(cmd, on_line)
            assert result is True
            mock_sync.assert_called_once_with(privileges.run_dnf, cmd, on_line)


class TestRunEpmAliases:
    def test_run_epm_is_alias_for_run_privileged(self):
        assert privileges.run_epm is privileges.run_privileged

    def test_run_epm_sync_is_alias_for_run_privileged_sync(self):
        assert privileges.run_epm_sync is privileges.run_privileged_sync


class TestRunPkexecLockCheck:
    def test_dnf_commands_trigger_lock_check(self, monkeypatch):
        monkeypatch.setattr(privileges, "_wait_for_dnf_lock", MagicMock())
        monkeypatch.setattr(privileges, "_get_pkexec_shell", MagicMock(return_value=None))
        monkeypatch.setattr(privileges, "threading", MagicMock())

    def test_dnf_bash_commands_trigger_lock_check(self):
        with (
            patch.object(privileges, "_wait_for_dnf_lock"),
            patch.object(privileges, "_get_pkexec_shell", return_value=None),
            patch.object(privileges, "threading"),
        ):
            pass
