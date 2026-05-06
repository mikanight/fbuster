"""Полные тесты core/packages.py — все парсеры, edge-кейсы, интеграции."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.packages import (
    InstallPreview,
    _detect_source_type,
    _extract_pkg_names,
    _parse_dnf_output,
    get_flatpak_system_updates,
    get_install_preview,
)


class TestDetectSourceTypeFull:
    def test_dnf_variants(self):
        assert _detect_source_type(["dnf", "upgrade"]) == "dnf"
        assert _detect_source_type(["dnf", "groupinstall", "group"]) == "dnf"
        assert _detect_source_type(["dnf", "reinstall", "pkg"]) == "dnf"
        assert _detect_source_type(["dnf", "distro-sync"]) == "dnf"

    def test_dnf5_variants(self):
        assert _detect_source_type(["dnf5", "install", "pkg"]) == "dnf"
        assert _detect_source_type(["dnf5", "upgrade"]) == "dnf"
        assert _detect_source_type(["dnf5", "autoremove"]) == "dnf"

    def test_flatpak_variants(self):
        assert _detect_source_type(["flatpak", "remote-add", "flathub", "url"]) == "flatpak"
        assert _detect_source_type(["flatpak", "update"]) == "flatpak"

    def test_other_package_managers(self):
        assert _detect_source_type(["apt", "install", "pkg"]) == "apt"
        assert _detect_source_type(["apt-get", "install", "pkg"]) == "apt"
        assert _detect_source_type(["epm", "install", "pkg"]) == "apt"


class TestExtractPkgNamesFull:
    def test_flatpak_extraction(self):
        result = _extract_pkg_names(["flatpak", "install", "flathub", "org.app"])
        assert result == ["flathub", "org.app"]

    def test_dnf5_with_long_opts(self):
        result = _extract_pkg_names([
            "dnf5", "install",
            "--best", "--allowerasing",
            "--setopt=fastestmirror=true",
            "htop",
            "--setopt=install_weak_deps=False",
            "tmux",
        ])
        assert result == ["htop", "tmux"]

    def test_single_flatpak_install(self):
        result = _extract_pkg_names(["flatpak", "install", "org.app"])
        assert result == ["org.app"]

    def test_epm_play(self):
        result = _extract_pkg_names(["epm", "play", "appname"])
        assert result == ["appname"]


class TestParseDnfOutputFull:
    def test_keeping_packages(self):
        lines = [
            "Installing dependencies:\n",
            " dep1  x86_64  1.0  fedora  1M\n",
            "Upgrading:\n",
            " old   x86_64  2.0  updates 0\n",
            "\n",
            "Total download size: 1 M\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["pkg"], False)
        assert "dep1" in preview.new_packages
        assert "old" in preview.upgraded_packages

    def test_size_formats(self):
        for line in [
            "Total download size: 1.5 GiB\n",
            "Общий размер загрузок: 500 KiB\n",
            "Total download size: 100 B\n",
        ]:
            preview = _parse_dnf_output([line], "dnf", [], False)
            assert preview.download_size != ""

    def test_no_sections(self):
        preview = _parse_dnf_output(["random output\n"], "dnf", ["pkg"], False)
        assert preview.source_type == "dnf"

    def test_apt_fallback_new_packages(self):
        lines = [
            "The following NEW packages will be installed:\n",
            "  pkg1 pkg2 pkg3\n",
            "0 upgraded, 3 newly installed, 0 to remove and 0 not upgraded.\n",
        ]
        preview = _parse_dnf_output(lines, "apt", ["pkg1", "pkg2", "pkg3"], False)
        assert len(preview.new_packages) == 3

    def test_apt_fallback_removed(self):
        lines = [
            "The following packages will be REMOVED:\n",
            "  pkg1\n",
            "0 upgraded, 0 newly installed, 1 to remove and 0 not upgraded.\n",
        ]
        preview = _parse_dnf_output(lines, "apt", ["pkg1"], False)
        assert len(preview.removed_packages) == 1


class TestGetInstallPreviewFull:
    def test_dnf_upgrade(self):
        preview = get_install_preview(["dnf", "upgrade"])
        assert preview.source_type == "dnf"

    def test_dnf_full_upgrade(self):
        preview = get_install_preview(["dnf", "full-upgrade"])
        assert preview.source_type == "dnf"

    def test_flatpak_install(self):
        preview = get_install_preview(["flatpak", "install", "flathub", "org.app"])
        assert preview.source_type == "flatpak"
        assert "org.app" in preview.package_names

    def test_script_command(self):
        preview = get_install_preview(["sh", "-c", "echo hello"])
        assert preview.source_type == "script"

    def test_dnf_install_with_runner(self):
        def runner(cmd, on_line):
            on_line("Installing:\n htop  x86_64  3.0  fedora  100k\n")
            on_line("Total download size: 100k\n")
            return True

        preview = get_install_preview(["dnf", "install", "htop", "tmux"], runner=runner)
        assert "htop" in preview.package_names
        assert preview.dry_run_failed is False


class TestGetFlatpakSystemUpdatesFull:
    def test_parses_multiple_updates(self):
        output = (
            " 1.\t[✗] org.app.One\tstable\t1.0\n"
            " 2.\t[✗] org.app.Two\tstable\t2.0\n"
            " 3.\t[✗] org.app.Three\tbeta\t3.0\n"
        )
        mock = MagicMock()
        mock.stdout = output
        mock.stderr = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            updates = get_flatpak_system_updates()
            assert len(updates) == 3

    def test_empty_output_returns_empty(self):
        mock = MagicMock()
        mock.stdout = ""
        mock.stderr = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            assert get_flatpak_system_updates() == []


class TestInstallPreviewDataclassFull:
    def test_all_fields_settable(self):
        p = InstallPreview(
            new_packages=["pkg1", "pkg2"],
            upgraded_packages=["old"],
            removed_packages=["rm"],
            kept_packages=["keep"],
            download_size="10 MiB",
            disk_space="25 MiB",
            warnings=["warning1"],
            errors=["error1"],
            dry_run_failed=False,
            source_type="dnf",
            package_names=["pkg1", "pkg2", "old"],
            app_version="1.0",
            app_description="Test app",
            flatpak_updates=["upd1"],
            app_url="https://app.example.com",
        )
        assert len(p.new_packages) == 2
        assert p.download_size == "10 MiB"
        assert p.source_type == "dnf"
        assert p.app_url == "https://app.example.com"

    def test_repr(self):
        p = InstallPreview(source_type="dnf", package_names=["test"])
        r = repr(p)
        assert "dnf" in r
        assert "test" in r
