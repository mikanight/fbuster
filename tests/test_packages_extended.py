"""Тесты core/packages.py — Flatpak и edge-кейсы."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.packages import (
    InstallPreview,
    _detect_source_type,
    _parse_dnf_output,
    get_flatpak_system_updates,
    get_install_preview,
)


class TestFlatpakSystemUpdates:
    def test_updates_found(self):
        output = " 1.\t[✗] org.gnome.Calculator\tstable\t46.1\n 2.\t[✗] org.gimp.GIMP\tstable\t2.10.38\n"
        mock = MagicMock()
        mock.stdout = output
        mock.stderr = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            updates = get_flatpak_system_updates()
            assert len(updates) == 2
            assert "org.gnome.Calculator" in updates
            assert "org.gimp.GIMP" in updates

    def test_no_updates(self):
        output = "Nothing to do.\n"
        mock = MagicMock()
        mock.stdout = output
        mock.stderr = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            updates = get_flatpak_system_updates()
            assert updates == []

    def test_subprocess_error(self):
        with patch("subprocess.run", side_effect=OSError):
            updates = get_flatpak_system_updates()
            assert updates == []

    def test_subprocess_timeout(self):
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.TimeoutExpired(["flatpak"], 20)):
            updates = get_flatpak_system_updates()
            assert updates == []


class TestGetInstallPreviewEdgeCases:
    def test_unknown_cmd_prefix(self):
        preview = get_install_preview(["custom-cmd", "install", "pkg"])
        assert preview.source_type == "script"
        assert preview.package_names == ["pkg"]

    def test_empty_cmd(self):
        preview = get_install_preview([])
        assert preview.source_type == "script"
        assert preview.package_names == []

    def test_flatpak_without_remote(self):
        preview = get_install_preview(["flatpak", "install", "org.app"])
        assert preview.source_type == "flatpak"
        assert preview.package_names == ["org.app"]

    def test_dnf_install_multiple_sources(self):
        preview = get_install_preview(["dnf", "install", "pkg1", "pkg2", "pkg3"])
        assert preview.source_type == "dnf"
        assert preview.package_names == ["pkg1", "pkg2", "pkg3"]

    def test_dnf_with_runner(self):
        def mock_runner(cmd, on_line):
            on_line("Installing:\n")
            on_line(" htop  x86_64  3.0  fedora  100k\n")
            on_line("Total download size: 100k\n")
            return True

        preview = get_install_preview(
            ["dnf", "install", "htop"],
            runner=mock_runner,
        )
        assert preview.source_type == "dnf"
        assert "htop" in preview.new_packages
        assert preview.dry_run_failed is False

    def test_dnf_with_runner_failure(self):
        def mock_runner(cmd, on_line):
            on_line("Error: package not found\n")
            return False

        preview = get_install_preview(
            ["dnf", "install", "unknown-pkg"],
            runner=mock_runner,
        )
        assert preview.dry_run_failed is True

    def test_dnf_with_runner_exception(self):
        def mock_runner(cmd, on_line):
            raise OSError("mock error")

        preview = get_install_preview(
            ["dnf", "install", "pkg"],
            runner=mock_runner,
        )
        assert preview.dry_run_failed is True


class TestInstallPreviewDataclass:
    def test_default_values(self):
        p = InstallPreview()
        assert p.new_packages == []
        assert p.upgraded_packages == []
        assert p.removed_packages == []
        assert p.kept_packages == []
        assert p.download_size == ""
        assert p.disk_space == ""
        assert p.warnings == []
        assert p.errors == []
        assert p.dry_run_failed is False
        assert p.source_type == "apt"
        assert p.package_names == []
        assert p.app_version == ""
        assert p.app_description == ""
        assert p.flatpak_updates == []
        assert p.app_url == ""

    def test_custom_values(self):
        p = InstallPreview(
            new_packages=["pkg1"],
            download_size="10 MiB",
            source_type="dnf",
            package_names=["pkg1"],
        )
        assert p.new_packages == ["pkg1"]
        assert p.download_size == "10 MiB"
        assert p.source_type == "dnf"


class TestParseDnfOutputEdgeCases:
    def test_empty_lines(self):
        preview = _parse_dnf_output([], "dnf", [], False)
        assert preview.source_type == "dnf"
        assert preview.new_packages == []

    def test_only_transaction_summary(self):
        lines = [
            "Transaction Summary\n",
            "Install  0 Packages\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", [], False)
        assert preview.new_packages == []

    def test_mixed_en_ru_sections(self):
        lines = [
            "Installing:\n",
            " gcc  x86_64  14.2.1  fedora  12 M\n",
            "Обновление:\n",
            " bash  x86_64  5.3.0  updates  0\n",
            "Removing:\n",
            " nano  x86_64  8.3  @System  580 k\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["gcc", "bash", "nano"], False)
        assert "gcc" in preview.new_packages
        assert "bash" in preview.upgraded_packages
        assert "nano" in preview.removed_packages

    def test_warnings_collected(self):
        lines = [
            "W: Possible missing firmware for module i915\n",
            "W: Repository fedora is listed more than once\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", [], False)
        assert len(preview.warnings) == 2

    def test_error_from_line(self):
        lines = [
            "Some output\n",
            "Error: Failed to download metadata for repo 'fedora'\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", [], True)
        assert len(preview.errors) == 1

    def test_apt_fallback_kept_packages(self):
        lines = [
            "The following packages have been kept back:\n",
            "  kernel kernel-devel\n",
            "0 upgraded, 0 newly installed, 0 to remove and 2 not upgraded.\n",
        ]
        preview = _parse_dnf_output(lines, "apt", [], False)
        assert len(preview.kept_packages) == 2
        assert "kernel" in preview.kept_packages

    def test_apt_fallback_need_to_get(self):
        lines = [
            "The following NEW packages will be installed:\n",
            "  gimp\n",
            "0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n",
            "Need to get 25 MB of archives.\n",
            "After this operation, 85 MB of additional disk space will be used.\n",
        ]
        preview = _parse_dnf_output(lines, "apt", ["gimp"], False)
        assert "25 MB" in preview.download_size
        assert "85 MB" in preview.disk_space


class TestDetectSourceTypeEdgeCases:
    def test_dnf5_returns_dnf(self):
        assert _detect_source_type(["dnf5", "install", "pkg"]) == "dnf"

    def test_epm_returns_apt(self):
        assert _detect_source_type(["epm", "-i", "pkg"]) == "apt"

    def test_apt_get_returns_apt(self):
        assert _detect_source_type(["apt-get", "install", "pkg"]) == "apt"

    def test_unlisted_pm_returns_script(self):
        assert _detect_source_type(["zypper", "install", "pkg"]) == "script"
        assert _detect_source_type(["pacman", "-S", "pkg"]) == "script"
