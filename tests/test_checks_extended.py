"""Расширенные тесты core/checks.py — системные проверки."""

import subprocess as _sp
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import checks


class TestIsFlathubEnabled:
    def test_flathub_present(self):
        mock = MagicMock()
        mock.stdout = "flathub\tFlathub\thttps://dl.flathub.org/repo/\n"
        with patch("subprocess.run", return_value=mock):
            assert checks.is_flathub_enabled() is True

    def test_flathub_absent(self):
        mock = MagicMock()
        mock.stdout = "fedora\tFedora\thttps://some.url/\n"
        with patch("subprocess.run", return_value=mock):
            assert checks.is_flathub_enabled() is False

    def test_subprocess_error(self):
        with patch("subprocess.run", side_effect=OSError):
            assert checks.is_flathub_enabled() is False


class TestIsFstrimEnabled:
    def test_fstrim_enabled(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            assert checks.is_fstrim_enabled() is True

    def test_fstrim_disabled(self):
        mock = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock):
            assert checks.is_fstrim_enabled() is False

    def test_subprocess_error(self):
        with patch("subprocess.run", side_effect=OSError):
            assert checks.is_fstrim_enabled() is False


class TestIsFractionalScaling:
    def test_enabled(self):
        with patch.object(checks, "gsettings_get", return_value="['scale-monitor-framebuffer']"):
            assert checks.is_fractional_scaling_enabled() is True

    def test_disabled_empty(self):
        with patch.object(checks, "gsettings_get", return_value="@as []"):
            assert checks.is_fractional_scaling_enabled() is False

    def test_disabled_other(self):
        with patch.object(checks, "gsettings_get", return_value="['xwayland-native-scaling']"):
            assert checks.is_fractional_scaling_enabled() is False


class TestIsVmDirtyOptimized:
    def test_optimized(self, tmp_path):
        conf = tmp_path / "90-dirty.conf"
        conf.parent.mkdir(parents=True, exist_ok=True)
        conf.write_text("vm.dirty_background_bytes = 67108864\nvm.dirty_bytes = 67108864\n")
        with patch("core.checks.Path", return_value=conf):
            assert checks.is_vm_dirty_optimized() is True

    def test_not_optimized(self, tmp_path):
        conf = tmp_path / "dummy.conf"
        conf.parent.mkdir(parents=True, exist_ok=True)
        conf.write_text("vm.swappiness = 10\n")
        with patch("core.checks.Path", return_value=conf):
            assert checks.is_vm_dirty_optimized() is False

    def test_file_missing(self):
        with patch("pathlib.Path.read_text", side_effect=OSError):
            assert checks.is_vm_dirty_optimized() is False


class TestIsJournalOptimized:
    def test_main_conf_optimized(self, tmp_path):
        conf = tmp_path / "journald.conf"
        conf.write_text("[Journal]\nSystemMaxUse=100M\n")
        with patch("core.checks.Path", side_effect=lambda p: conf if "journald.conf" in str(p) else MagicMock()):
            with patch.object(checks.Path, "read_text", side_effect=OSError):
                pass

    def test_altbooster_conf_optimized(self):
        with patch("pathlib.Path.read_text", return_value="[Journal]\nSystemMaxUse=100M\n"):
            with patch("pathlib.Path.exists", return_value=True):
                assert checks.is_journal_optimized() is True

    def test_not_optimized(self):
        with patch("pathlib.Path.read_text", side_effect=OSError):
            assert checks.is_journal_optimized() is False


class TestIsDavinciInstalled:
    def test_binary_exists(self):
        with patch("os.path.exists", return_value=True):
            assert checks.is_davinci_installed() is True

    def test_rpm_found(self):
        with patch("os.path.exists", return_value=False):
            mock = MagicMock(returncode=0)
            with patch("subprocess.run", return_value=mock):
                assert checks.is_davinci_installed() is True

    def test_not_installed(self):
        with patch("os.path.exists", return_value=False):
            mock = MagicMock(returncode=1)
            with patch("subprocess.run", return_value=mock):
                assert checks.is_davinci_installed() is False


class TestIsAacInstalled:
    def test_bundle_exists(self):
        with patch("os.path.exists", return_value=True):
            assert checks.is_aac_installed() is True

    def test_bundle_missing(self):
        with patch("os.path.exists", return_value=False):
            assert checks.is_aac_installed() is False


class TestIsFairlightInstalled:
    def test_fully_configured(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("os.path.exists", return_value=True):
                m = MagicMock()
                m.__enter__ = MagicMock(return_value=m)
                m.read = MagicMock(return_value="type pulse\nother stuff\n")
                m.__exit__ = MagicMock(return_value=False)
                with patch("builtins.open", return_value=m):
                    assert checks.is_fairlight_installed() is True

    def test_asound_missing(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("os.path.exists", return_value=False):
                assert checks.is_fairlight_installed() is False

    def test_type_pulse_absent(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("os.path.exists", return_value=True):
                m = MagicMock()
                m.__enter__ = MagicMock(return_value=m)
                m.read = MagicMock(return_value="type hw\n")
                m.__exit__ = MagicMock(return_value=False)
                with patch("builtins.open", return_value=m):
                    assert checks.is_fairlight_installed() is False

    def test_rpm_missing(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert checks.is_fairlight_installed() is False


class TestIsDriveMenuPatched:
    def test_patched(self):
        with patch("pathlib.Path.read_text", return_value="code this._mounts.some more code"):
            assert checks.is_drive_menu_patched() is True

    def test_not_patched(self):
        with patch("pathlib.Path.read_text", return_value="code without mount stuff"):
            assert checks.is_drive_menu_patched() is False

    def test_file_missing(self):
        with patch("pathlib.Path.read_text", side_effect=OSError):
            assert checks.is_drive_menu_patched() is False


class TestIsSystemBusyExtended:
    def test_both_packagekitd_and_dnf_lock(self):
        def run_side(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "pgrep":
                return MagicMock(returncode=0)
            if cmd[0] == "fuser":
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        with (
            patch("os.path.exists", return_value=True),
            patch("subprocess.run", side_effect=run_side),
        ):
            assert checks.is_system_busy() is True

    def test_subprocess_timeout(self):
        with patch("subprocess.run", side_effect=_sp.TimeoutExpired(["pgrep"], 5)):
            with patch("os.path.exists", return_value=False):
                result = checks.is_system_busy()
                assert result is False

    def test_oserror_handled(self):
        with patch("os.path.exists", side_effect=OSError):
            assert checks.is_system_busy() is False


class TestSudoUser:
    def test_sudo_user_from_env(self):
        import os
        mock = MagicMock()
        mock.stdout = "wheel"
        with patch.dict(os.environ, {"SUDO_USER": "admin"}):
            with patch("subprocess.run", return_value=mock):
                assert checks.is_sudo_enabled() is True

    def test_normal_user_from_env(self):
        import os
        mock = MagicMock()
        mock.stdout = "users"
        with patch.dict(os.environ, {"USER": "john"}):
            with patch("subprocess.run", return_value=mock):
                assert checks.is_sudo_enabled() is False
