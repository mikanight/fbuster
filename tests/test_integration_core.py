"""Интеграционные тесты — взаимодействие модулей core."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import backend, config
from core.borg import DEFAULT_EXCLUDES, OPTIONAL_EXCLUDES, _borg_exe
from core.mirror import (
    _ALWAYS_EXCLUDES,
    OPTIONAL_ITEMS,
    detect_mirror_type,
    get_root_partition_disk,
    get_root_filesystem,
    is_uefi,
    list_available_disks,
)
from core.btrfs import get_btrfs_mount_for_home, get_snapshots_dir


class TestConfigBorgIntegration:
    """Интеграция config и borg."""

    def test_config_dir_used_by_borg(self, tmp_path):
        config.CONFIG_DIR = tmp_path
        config.STATE_FILE = tmp_path / "state.json"
        config.reset_state()
        config.state_set("borg_passphrase", "secret123")
        assert config.state_get("borg_passphrase") == "secret123"

    def test_systemd_user_dir_accessible(self):
        assert config.SYSTEMD_USER_DIR is not None


class TestBackendFacade:
    """Фасад backend должен реэкспортировать ключевые функции."""

    def test_backend_exports_borg_functions(self):
        assert callable(backend.is_borg_installed)
        assert callable(backend.is_repo_initialized)

    def test_backend_exports_checks_functions(self):
        assert callable(backend.is_flathub_enabled)
        assert callable(backend.is_system_busy)
        assert callable(backend.check_app_installed)

    def test_backend_exports_default_excludes(self):
        assert isinstance(backend.DEFAULT_EXCLUDES, list)
        assert len(backend.DEFAULT_EXCLUDES) > 0

    def test_backend_exports_run_privileged(self):
        assert callable(backend.run_privileged)
        assert callable(backend.run_privileged_sync)

    def test_backend_exports_state_management(self):
        config.state_set("test_backend", 42)
        assert config.state_get("test_backend") == 42


class TestMirrorBtrfsIntegration:
    """Интеграция mirror и btrfs через интерфейс конфигурации."""

    def test_snapshot_dir_used_in_mirror_filters(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        snap_dir = get_snapshots_dir()
        assert isinstance(snap_dir, Path)
        assert "fedorabooster" in str(snap_dir)

    def test_mirror_excludes_use_proper_paths(self):
        assert "/proc" in _ALWAYS_EXCLUDES
        assert "/sys" in _ALWAYS_EXCLUDES
        assert "/dev" in _ALWAYS_EXCLUDES
        assert "/tmp" in _ALWAYS_EXCLUDES
        assert "/run" in _ALWAYS_EXCLUDES
        assert "/lost+found" in _ALWAYS_EXCLUDES


class TestMirrorModuleFunctions:
    """Функции mirror.py работают корректно."""

    def test_detect_mirror_type_nonexistent(self):
        assert detect_mirror_type("/nonexistent/path") is None

    def test_detect_mirror_type_rsync(self, tmp_path):
        folder = tmp_path / "mirror"
        folder.mkdir()
        (folder / "rootfs").mkdir()
        result = detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "rsync"

    def test_detect_mirror_type_btrfs(self, tmp_path):
        folder = tmp_path / "mirror"
        folder.mkdir()
        (folder / "root.btrfs").touch()
        result = detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "btrfs"

    def test_detect_mirror_type_tar(self, tmp_path):
        folder = tmp_path / "mirror"
        folder.mkdir()
        (folder / "rootfs-2024.tar.gz").touch()
        result = detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "tar"

    def test_get_root_partition_disk_various(self):
        assert get_root_partition_disk("/dev/nvme0n1p2") == "/dev/nvme0n1"
        assert get_root_partition_disk("/dev/sda5") == "/dev/sda"
        assert get_root_partition_disk("/dev/mmcblk0p3") == "/dev/mmcblk0"
        assert get_root_partition_disk("/dev/vda1") == "/dev/vda"
        assert get_root_partition_disk(None) == ""
        assert get_root_partition_disk("") == ""

    def test_is_uefi(self):
        with patch("os.path.isdir", return_value=True):
            assert is_uefi() is True
        with patch("os.path.isdir", return_value=False):
            assert is_uefi() is False

    def test_get_root_filesystem(self):
        with patch("subprocess.check_output", return_value="btrfs\n"):
            assert get_root_filesystem() == "btrfs"
        with patch("subprocess.check_output", return_value="ext4\n"):
            assert get_root_filesystem() == "ext4"
        with patch("subprocess.check_output", side_effect=OSError):
            assert get_root_filesystem() is None

    def test_list_available_disks_excludes_loop(self):
        out = "sda   256G  Samsung\nloop0  50M  model  loop\n"
        with (
            patch("subprocess.check_output", return_value=out),
            patch("core.mirror.get_root_device", return_value="/dev/sda1"),
        ):
            disks = list_available_disks()
            for d in disks:
                assert d["type"] != "loop"


class TestConstantsConsistency:
    """Константы консистентны между модулями."""

    def test_optional_excludes_vs_default_excludes(self):
        optional_paths = set()
        for group in OPTIONAL_EXCLUDES:
            for p in group["paths"]:
                optional_paths.add(p.replace("~", str(Path.home())))
        assert len(optional_paths) > 0

    def test_optional_items_have_valid_structure(self):
        for item in OPTIONAL_ITEMS:
            assert "key" in item
            assert "path" in item
            assert "label" in item
            assert "default" in item

    def test_default_excludes_list_is_list_of_strings(self):
        for e in DEFAULT_EXCLUDES:
            assert isinstance(e, str)

    def test_flathub_mirrors_are_valid(self):
        from tabs.flatpak import _FLATHUB_MIRRORS
        for name, domain, url in _FLATHUB_MIRRORS:
            assert isinstance(name, str)
            assert isinstance(domain, str)
            assert isinstance(url, str)
            assert url.startswith("https://")
            assert ".flathub.org" in domain or "mirror" in domain
