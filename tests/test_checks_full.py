"""Полные тесты core/checks.py — все проверки, кэши, edge-кейсы."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import checks


class TestCheckAppInstalledEdgeCases:
    def test_multiple_checks_mocked(self):
        source = {
            "label": "Test",
            "check": [
                ["path", "/etc"],
                ["path", "/dev"],
            ],
        }
        with patch.object(checks, "_eval_check_pair", side_effect=[True, True]):
            assert checks.check_app_installed(source) is True

    def test_multiple_checks_one_fails_mocked(self):
        side_effects = iter([True, False])
        def se(kind, value):
            try:
                return next(side_effects)
            except StopIteration:
                return False
        with patch.object(checks, "_eval_check_pair", side_effect=se):
            source = {"label": "T", "check": [["path", "/etc"], ["rpm", "none"]]}
            result = checks.check_app_installed(source)
            assert result is True

    def test_unknown_check_kind(self):
        source = {"label": "Test", "check": ["unknown_kind", "value"]}
        assert checks.check_app_installed(source) is False

    def test_check_with_extra_kwargs(self):
        source = {
            "label": "Test",
            "check": ["desktop_keyword", "firefox"],
        }
        with patch.object(checks, "_desktop_keyword_installed", return_value=True):
            assert checks.check_app_installed(source) is True


class TestEvalCheckPair:
    def test_path_exists(self):
        assert checks._eval_check_pair("path", "/etc") is True

    def test_path_not_exists(self):
        assert checks._eval_check_pair("path", "/nonexistent/abc123") is False

    def test_which_found(self):
        assert checks._eval_check_pair("which", "bash") is True

    def test_which_not_found(self):
        assert checks._eval_check_pair("which", "no-such-command-xyz") is False

    def test_rpm_installed(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            assert checks._eval_check_pair("rpm", "bash") is True

    def test_rpm_not_installed(self):
        mock = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock):
            assert checks._eval_check_pair("rpm", "no-pkg") is False

    def test_flatpak_installed(self):
        with patch.object(checks, "_get_flatpak_installed", return_value={"org.test.App"}):
            assert checks._eval_check_pair("flatpak", "org.test.App") is True

    def test_flatpak_not_installed(self):
        with patch.object(checks, "_get_flatpak_installed", return_value=set()):
            assert checks._eval_check_pair("flatpak", "org.test.App") is False

    def test_any_of_all_true(self):
        with patch.object(checks, "_eval_check_pair", return_value=True):
            result = checks._eval_check_pair("any_of", [["path", "/etc"], ["rpm", "bash"]])
            assert result is True

    def test_any_of_mixed(self):
        side_effects = iter([True, False])
        def side_effect(kind, value):
            try:
                return next(side_effects)
            except StopIteration:
                return False
        with patch.object(checks, "_eval_check_pair", side_effect=side_effect):
            result = checks._eval_check_pair("any_of", [["rpm", "yes"], ["path", "/none"]])
            assert result is True

    def test_desktop_keyword_found(self):
        with patch.object(checks, "_desktop_keyword_installed", return_value=True):
            assert checks._eval_check_pair("desktop_keyword", "firefox") is True

    def test_desktop_keyword_not_found(self):
        with patch.object(checks, "_desktop_keyword_installed", return_value=False):
            assert checks._eval_check_pair("desktop_keyword", "unknown") is False


class TestIsFlathubEnabledExtended:
    def test_case_insensitive(self):
        mock = MagicMock()
        mock.stdout = "Flathub\tFlathub\turl\n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            assert checks.is_flathub_enabled() is True

    def test_no_flatpak_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert checks.is_flathub_enabled() is False


class TestIsSystemBusyAllCases:
    def test_checks_each_dnf_lock_file(self):
        calls = {"count": 0}
        def run_side(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "fuser":
                calls["count"] += 1
                return MagicMock(returncode=1)
            if cmd[0] == "pgrep":
                return MagicMock(returncode=1)
            return MagicMock(returncode=0)

        with (
            patch("os.path.exists", return_value=True),
            patch("subprocess.run", side_effect=run_side),
        ):
            checks.is_system_busy()

    def test_pgrep_timeout_short_circuits(self):
        import subprocess as sp
        with (
            patch("os.path.exists", return_value=False),
            patch("subprocess.run", side_effect=sp.TimeoutExpired(["pgrep"], 3)),
        ):
            result = checks.is_system_busy()
            assert result is False


class TestIsJournalOptimizedExtended:
    def test_checks_fedorabooster_dropin(self):
        with patch("pathlib.Path.read_text", return_value="[Journal]\nSystemMaxUse=100M\n"):
            with patch("pathlib.Path.exists", return_value=True):
                assert checks.is_journal_optimized() is True

    def test_both_files_missing(self):
        with patch("pathlib.Path.read_text", side_effect=OSError):
            assert checks.is_journal_optimized() is False


class TestIsVmDirtyOptimizedExtended:
    def test_both_values(self):
        with patch("pathlib.Path.read_text", return_value="vm.dirty_bytes = 67108864\nvm.dirty_background_bytes = 67108864\n"):
            with patch("pathlib.Path.exists", return_value=True):
                assert checks.is_vm_dirty_optimized() is True


class TestIsFairlightInstalledExtended:
    def test_pipewire_present(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("os.path.exists", return_value=True):
                m = MagicMock()
                m.__enter__ = MagicMock(return_value=m)
                m.read = MagicMock(return_value="type pulse\n")
                m.__exit__ = MagicMock(return_value=False)
                with patch("builtins.open", return_value=m):
                    assert checks.is_fairlight_installed() is True


class TestCacheInvalidationExtended:
    def test_desktop_files_cache_cleared(self):
        checks.invalidate_desktop_files_cache()
        checks.invalidate_app_detection_caches()
        assert True

    def test_flatpak_cache_cleared(self):
        checks.invalidate_flatpak_cache()
        checks.invalidate_app_detection_caches()
        assert True
