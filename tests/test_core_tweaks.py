"""Тесты core/tweaks.py — apply_vm_dirty, patch_drive_menu, install_aac_codec."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.tweaks import apply_vm_dirty, install_aac_codec, patch_drive_menu


class TestApplyVmDirty:
    def test_runs_privileged_command(self):
        on_log = MagicMock()
        on_done = MagicMock()
        with patch("core.tweaks.run_privileged") as mock_run:
            apply_vm_dirty(on_log, on_done)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0]
            assert "vm.dirty_bytes = 67108864" in call_args[0][2]
            assert "vm.dirty_background_bytes = 16777216" in call_args[0][2]
            assert call_args[1] is on_log
            assert call_args[2] is on_done


class TestInstallAacCodec:
    def test_runs_bash_extract_and_copy(self):
        on_line = MagicMock()
        on_done = MagicMock()
        archive = "/tmp/test_aac.tar.gz"
        with patch("core.tweaks.run_privileged") as mock_run:
            install_aac_codec(archive, on_line, on_done)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0]
            assert "tar --no-symlinks" in call_args[0][2]
            assert "/tmp/aac_encoder_plugin.dvcp.bundle" in call_args[0][2]
            assert call_args[1] is on_line
            assert call_args[2] is on_done


class TestPatchDriveMenu:
    def test_creates_temp_patch_and_runs_script(self):
        on_log = MagicMock()
        on_done = MagicMock()
        with (
            patch("core.tweaks.tempfile.mkstemp", return_value=(42, "/tmp/fedorabooster_drive_xxx.patch")),
            patch("core.tweaks.os.fdopen") as mock_fdopen,
            patch("core.tweaks.run_privileged") as mock_run,
            patch("core.tweaks.os.unlink"),
        ):
            mock_file = MagicMock()
            mock_fdopen.return_value.__enter__.return_value = mock_file

            patch_drive_menu(on_log, on_done)

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0]
            script = call_args[0][2]
            assert "drive-menu@gnome-shell-extensions" in script
            assert "this._mounts.some" in script
            assert "patch" in script
        mock_file.write.assert_called_once()

    def test_handles_write_failure(self):
        on_log = MagicMock()
        on_done = MagicMock()
        with (
            patch("core.tweaks.tempfile.mkstemp", return_value=(42, "/tmp/fedorabooster_drive_xxx.patch")),
            patch("core.tweaks.os.fdopen", side_effect=OSError),
            patch("core.tweaks.os.unlink"),
            patch("core.tweaks.run_privileged"),
        ):
            patch_drive_menu(on_log, on_done)
            on_done.assert_called_once_with(False)
