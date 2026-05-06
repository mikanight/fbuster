"""Расширенные тесты core/mirror.py — edge-кейсы и интеграции."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.mirror import (
    OPTIONAL_ITEMS,
    _ALWAYS_EXCLUDES,
    detect_mirror_type,
    get_dest_filesystem,
    get_root_device,
    get_root_filesystem,
    get_root_partition_disk,
    is_uefi,
    list_available_disks,
    list_btrfs_subvolumes,
)


class TestDetectMirrorTypeEdgeCases:
    def test_empty_folder(self, tmp_path):
        folder = tmp_path / "empty"
        folder.mkdir()
        assert detect_mirror_type(str(folder)) is None

    def test_rsync_and_tar_both_present(self, tmp_path):
        folder = tmp_path / "mirror"
        folder.mkdir()
        (folder / "rootfs").mkdir()
        (folder / "rootfs-2024.tar.gz").touch()
        result = detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "rsync"


class TestListAvailableDisksEdgeCases:
    def test_mixed_disks_and_loops(self):
        out = "sda   256G  Samsung\nloop0  1G  squashfs\nnvme0n1  512G  WD_Black\nloop1  50M  tmp\n"
        with (
            patch("subprocess.check_output", return_value=out),
            patch("core.mirror.get_root_device", return_value="/dev/nvme0n1p2"),
        ):
            disks = list_available_disks()
            names = [d["name"] for d in disks]
            assert "sda" in names

    def test_single_physical_disk_no_root(self):
        out = "sda   128G  Samsung\n"
        with (
            patch("subprocess.check_output", return_value=out),
            patch("core.mirror.get_root_device", return_value=None),
        ):
            disks = list_available_disks()
            assert len(disks) == 1
            assert disks[0]["name"] == "sda"


class TestListBtrfsSubvolumesEdgeCases:
    def test_unicode_in_paths(self):
        out = "ID 256 gen 100 top level 5 path @дом\n"
        with patch("subprocess.check_output", return_value=out):
            result = list_btrfs_subvolumes()
            assert len(result) == 1
            assert result[0]["path"] == "@дом"

    def test_multiple_snapshots(self):
        out = (
            "ID 256 gen 100 top level 5 path @\n"
            "ID 257 gen 101 top level 5 path @home\n"
            "ID 258 gen 102 top level 5 path @snap_2024\n"
            "ID 259 gen 103 top level 5 path @snap_2025\n"
        )
        with patch("subprocess.check_output", return_value=out):
            result = list_btrfs_subvolumes()
            assert len(result) == 4


class TestGetRootDeviceEdgeCases:
    def test_lvm_device(self):
        with patch("subprocess.check_output", return_value="/dev/mapper/fedora-root\n"):
            result = get_root_device()
            assert result == "/dev/mapper/fedora-root"

    def test_newline_handling(self):
        with patch("subprocess.check_output", return_value="/dev/sda2\n\n"):
            result = get_root_device()
            assert result == "/dev/sda2"


class TestOptionalItems:
    def test_keys_are_strings(self):
        for item in OPTIONAL_ITEMS:
            assert isinstance(item["key"], str)
            assert isinstance(item["label"], str)

    def test_defaults_are_booleans(self):
        for item in OPTIONAL_ITEMS:
            assert isinstance(item["default"], bool)

    def test_paths_are_strings(self):
        for item in OPTIONAL_ITEMS:
            assert isinstance(item["path"], str)


class TestAlwaysExcludes:
    def test_exclude_count(self):
        assert len(_ALWAYS_EXCLUDES) >= 5

    def test_all_are_strings(self):
        for e in _ALWAYS_EXCLUDES:
            assert isinstance(e, str)

    def test_no_duplicates(self):
        assert len(_ALWAYS_EXCLUDES) == len(set(_ALWAYS_EXCLUDES))


class TestGetFilesystemsEdgeCases:
    def test_xfs(self):
        with patch("subprocess.check_output", return_value="xfs\n"):
            assert get_root_filesystem() == "xfs"

    def test_f2fs(self):
        with patch("subprocess.check_output", return_value="f2fs\n"):
            assert get_root_filesystem() == "f2fs"

    def test_dest_fs_vfat(self):
        with patch("subprocess.check_output", return_value="vfat\n"):
            assert get_dest_filesystem("/mnt/usb") == "vfat"
