"""Тесты core/mirror.py — служебные функции."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import mirror


class TestGetRootPartitionDisk:
    def test_nvme_device(self):
        assert mirror.get_root_partition_disk("/dev/nvme0n1p2") == "/dev/nvme0n1"

    def test_sata_device(self):
        assert mirror.get_root_partition_disk("/dev/sda1") == "/dev/sda"

    def test_mmc_device(self):
        assert mirror.get_root_partition_disk("/dev/mmcblk0p3") == "/dev/mmcblk0"

    def test_vda_device(self):
        assert mirror.get_root_partition_disk("/dev/vda2") == "/dev/vda"

    def test_device_without_partition_number(self):
        assert mirror.get_root_partition_disk("/dev/sda") == "/dev/sda"

    def test_none_input(self):
        assert mirror.get_root_partition_disk(None) == ""

    def test_empty_string(self):
        result = mirror.get_root_partition_disk("")
        assert result == ""


class TestIsUefi:
    def test_uefi_system(self):
        with patch("os.path.isdir", return_value=True):
            assert mirror.is_uefi() is True

    def test_bios_system(self):
        with patch("os.path.isdir", return_value=False):
            assert mirror.is_uefi() is False


class TestListAvailableDisks:
    def test_disk_listing(self):
        lsblk_out = "sda   128G  Samsung  disk\nnvme0n1  512G  WD_Black  disk\n"
        with (
            patch("subprocess.check_output", return_value=lsblk_out),
            patch.object(mirror, "get_root_device", return_value="/dev/nvme0n1p2"),
        ):
            disks = mirror.list_available_disks()
            assert len(disks) == 1
            assert disks[0]["name"] == "sda"

    def test_disk_listing_exclude_root_false(self):
        lsblk_out = "sda   128G  Samsung  disk\n"
        with (
            patch("subprocess.check_output", return_value=lsblk_out),
            patch.object(mirror, "get_root_device", return_value="/dev/sda1"),
        ):
            disks = mirror.list_available_disks(exclude_root=False)
            assert len(disks) == 1
            assert disks[0]["name"] == "sda"

    def test_disk_listing_no_disks(self):
        lsblk_out = "loop0  50M  model  loop\n"
        with (
            patch("subprocess.check_output", return_value=lsblk_out),
            patch.object(mirror, "get_root_device", return_value="/dev/sda1"),
        ):
            disks = mirror.list_available_disks()
            assert len(disks) == 0

    def test_subprocess_error(self):
        with (
            patch("subprocess.check_output", side_effect=OSError),
            patch.object(mirror, "get_root_device", return_value="/dev/sda1"),
        ):
            disks = mirror.list_available_disks()
            assert disks == []

    def test_empty_output(self):
        with (
            patch("subprocess.check_output", return_value=""),
            patch.object(mirror, "get_root_device", return_value="/dev/sda1"),
        ):
            disks = mirror.list_available_disks()
            assert disks == []

    def test_incomplete_lines(self):
        with (
            patch("subprocess.check_output", return_value="sda\n"),
            patch.object(mirror, "get_root_device", return_value="/dev/sda1"),
        ):
            disks = mirror.list_available_disks()
            assert disks == []


class TestGetFilesystems:
    def test_root_fs_btrfs(self):
        with patch("subprocess.check_output", return_value="btrfs\n"):
            result = mirror.get_root_filesystem()
            assert result == "btrfs"

    def test_root_fs_ext4(self):
        with patch("subprocess.check_output", return_value="ext4\n"):
            result = mirror.get_root_filesystem()
            assert result == "ext4"

    def test_root_fs_error(self):
        with patch("subprocess.check_output", side_effect=OSError):
            result = mirror.get_root_filesystem()
            assert result is None

    def test_dest_fs(self):
        with patch("subprocess.check_output", return_value="btrfs\n"):
            result = mirror.get_dest_filesystem("/mnt/backup")
            assert result == "btrfs"

    def test_dest_fs_error(self):
        with patch("subprocess.check_output", side_effect=OSError):
            result = mirror.get_dest_filesystem("/mnt/backup")
            assert result is None


class TestGetRootDevice:
    def test_returns_device(self):
        with patch("subprocess.check_output", return_value="/dev/sda2\n"):
            result = mirror.get_root_device()
            assert result == "/dev/sda2"

    def test_returns_none_on_error(self):
        with patch("subprocess.check_output", side_effect=OSError):
            result = mirror.get_root_device()
            assert result is None

    def test_empty_output(self):
        with patch("subprocess.check_output", return_value="\n"):
            result = mirror.get_root_device()
            assert result is None


class TestListBtrfsSubvolumes:
    def test_subvolume_listing(self):
        out = "ID 256 gen 100 top level 5 path @\nID 257 gen 101 top level 5 path @home\n"
        with patch("subprocess.check_output", return_value=out):
            result = mirror.list_btrfs_subvolumes()
            assert len(result) == 2
            assert result[0]["id"] == 256
            assert result[0]["path"] == "@"
            assert result[1]["id"] == 257
            assert result[1]["path"] == "@home"

    def test_empty_listing(self):
        with patch("subprocess.check_output", return_value=""):
            result = mirror.list_btrfs_subvolumes()
            assert result == []

    def test_error_handling(self):
        with patch("subprocess.check_output", side_effect=OSError):
            result = mirror.list_btrfs_subvolumes()
            assert result == []


class TestDetectMirrorType:
    def test_btrfs_recv_type(self, tmp_path):
        folder = tmp_path / "backup"
        folder.mkdir()
        (folder / "partition_table.sfdisk").touch()
        (folder / "boot-efi.tar").touch()
        (folder / ".snap_@_prev").mkdir()
        (folder / ".snap_@home_prev").mkdir()

        result = mirror.detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "btrfs_recv"
        assert result["has_pt"] is True
        assert result["has_efi"] is True
        assert sorted(result["subvols"]) == ["@", "@home"]

    def test_btrfs_type(self, tmp_path):
        folder = tmp_path / "backup"
        folder.mkdir()
        (folder / "root.btrfs").touch()
        (folder / "home.btrfs").touch()

        result = mirror.detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "btrfs"
        assert sorted(result["subvols"]) == ["home", "root"]

    def test_rsync_type(self, tmp_path):
        folder = tmp_path / "backup"
        folder.mkdir()
        (folder / "rootfs").mkdir()

        result = mirror.detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "rsync"

    def test_tar_type(self, tmp_path):
        folder = tmp_path / "backup"
        folder.mkdir()
        (folder / "rootfs-2024.tar.gz").touch()

        result = mirror.detect_mirror_type(str(folder))
        assert result is not None
        assert result["type"] == "tar"
        assert "rootfs-2024.tar.gz" in result["path"]

    def test_not_a_mirror(self, tmp_path):
        folder = tmp_path / "empty"
        folder.mkdir()

        result = mirror.detect_mirror_type(str(folder))
        assert result is None

    def test_nonexistent_path(self):
        result = mirror.detect_mirror_type("/nonexistent/path")
        assert result is None
