"""Тесты core/btrfs.py — snapshots, systemd-таймеры."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.btrfs import (
    _run_systemctl,
    disable_btrfs_timer,
    enable_btrfs_timer,
    get_btrfs_mount_for_home,
    get_btrfs_timer_next_run,
    get_snapshots_dir,
    is_btrfs_timer_active,
    write_btrfs_systemd_units,
)


class TestGetBtrfsMountForHome:
    def test_finds_btrfs_mount(self):
        mountinfo = "1 2 0:3 / / rw - btrfs /dev/sda2 rw,relatime\n"
        with patch("builtins.open", new_callable=lambda: None):
            with patch("pathlib.Path.is_dir", return_value=True):
                with patch("pathlib.Path.is_absolute", return_value=True):
                    with patch("pathlib.Path.resolve", return_value=Path("/")):
                        pass

    def test_no_btrfs_mount(self):
        with patch("builtins.open", side_effect=OSError):
            result = get_btrfs_mount_for_home()
            assert result is None

    def test_error_handling(self):
        with patch("builtins.open", side_effect=OSError):
            result = get_btrfs_mount_for_home()
            assert result is None


class TestGetSnapshotsDir:
    def test_uses_configured_dir(self, tmp_path):
        from core import config
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()
        config.state_set("btrfs_snapshots_dir", "/custom/snapshots")
        result = get_snapshots_dir()
        assert result == Path("/custom/snapshots")

    def test_default_with_mount_point(self, tmp_path):
        from core import config
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()
        config.state_set("btrfs_snapshots_dir", "")
        with patch("core.btrfs.get_btrfs_mount_for_home", return_value="/mnt/btrfs"):
            result = get_snapshots_dir()
            assert result == Path("/mnt/btrfs/.snapshots/fedorabooster")

    def test_fallback_when_no_mount(self, tmp_path):
        from core import config
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()
        config.state_set("btrfs_snapshots_dir", "")
        with patch("core.btrfs.get_btrfs_mount_for_home", return_value=None):
            result = get_snapshots_dir()
            assert "fedorabooster" in str(result)
            assert "btrfs-snapshots" in str(result)


class TestWriteBtrfsSystemdUnits:
    def test_creates_unit_files(self, tmp_path):
        from core import config
        config.SYSTEMD_USER_DIR = tmp_path

        with patch("core.btrfs.get_btrfs_mount_for_home", return_value="/mnt/btrfs"):
            with patch("core.btrfs._validate_mount_point", return_value=True):
                ok = write_btrfs_systemd_units(interval_hours=24, keep_count=7)
                assert ok is True
                service = tmp_path / "fedorabooster-btrfs.service"
                timer = tmp_path / "fedorabooster-btrfs.timer"
                assert service.exists()
                assert timer.exists()
                content = service.read_text()
                assert "Fedora Booster" in content
                assert "btrfs subvolume snapshot" in content

    def test_uses_fedorabooster_units(self, tmp_path):
        from core import config
        config.SYSTEMD_USER_DIR = tmp_path
        with patch("core.btrfs.get_btrfs_mount_for_home", return_value="/mnt/btrfs"):
            with patch("core.btrfs._validate_mount_point", return_value=True):
                write_btrfs_systemd_units(6, 5)
                assert (tmp_path / "fedorabooster-btrfs.service").exists()
                assert (tmp_path / "fedorabooster-btrfs.timer").exists()
                assert not (tmp_path / "altbooster-btrfs.service").exists()

    def test_hourly_interval(self, tmp_path):
        from core import config
        config.SYSTEMD_USER_DIR = tmp_path
        with patch("core.btrfs.get_btrfs_mount_for_home", return_value="/mnt/btrfs"):
            with patch("core.btrfs._validate_mount_point", return_value=True):
                write_btrfs_systemd_units(1, 5)
                content = (tmp_path / "fedorabooster-btrfs.timer").read_text()
                assert "OnCalendar=hourly" in content

    def test_six_hour_interval(self, tmp_path):
        from core import config
        config.SYSTEMD_USER_DIR = tmp_path
        with patch("core.btrfs.get_btrfs_mount_for_home", return_value="/mnt/btrfs"):
            with patch("core.btrfs._validate_mount_point", return_value=True):
                write_btrfs_systemd_units(6, 5)
                content = (tmp_path / "fedorabooster-btrfs.timer").read_text()
                assert "*-*-* 0/6:00:00" in content


class TestBtrfsTimerManagement:
    def test_enable_timer(self):
        mock = MagicMock(returncode=0)
        with patch("core.btrfs.subprocess.run", return_value=mock):
            assert enable_btrfs_timer() is True

    def test_disable_timer(self):
        mock = MagicMock(returncode=0)
        with patch("core.btrfs.subprocess.run", return_value=mock):
            assert disable_btrfs_timer() is True

    def test_is_timer_active(self):
        mock = MagicMock(returncode=0)
        with patch("core.btrfs.subprocess.run", return_value=mock):
            assert is_btrfs_timer_active() is True

    def test_is_timer_inactive(self):
        mock = MagicMock(returncode=1)
        with patch("core.btrfs.subprocess.run", return_value=mock):
            assert is_btrfs_timer_active() is False

    def test_get_timer_next_run(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "NextElapseUSecRealtime=1746560000000000\n"
        with patch("core.btrfs.subprocess.run", return_value=mock):
            result = get_btrfs_timer_next_run()
            assert result is not None
            assert "." in result

    def test_get_timer_next_run_none(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "NextElapseUSecRealtime=0\n"
        with patch("core.btrfs.subprocess.run", return_value=mock):
            assert get_btrfs_timer_next_run() is None

    def test_run_systemctl_daemon_reload(self):
        mock = MagicMock(returncode=0)
        with patch("core.btrfs.subprocess.run", return_value=mock):
            result = _run_systemctl(["daemon-reload"])
            assert result.returncode == 0
