"""Тесты core/packages.py — Фаза 1."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.packages import (
    _detect_source_type,
    _parse_dnf_output,
    _extract_pkg_names,
    get_install_preview,
    InstallPreview,
)


class TestDetectSourceType:
    def test_empty_cmd_returns_script(self):
        assert _detect_source_type([]) == "script"

    def test_flatpak_returns_flatpak(self):
        assert _detect_source_type(["flatpak", "install", "flathub", "org.app"]) == "flatpak"

    def test_dnf_returns_dnf(self):
        assert _detect_source_type(["dnf", "install", "package"]) == "dnf"

    def test_dnf5_returns_dnf(self):
        assert _detect_source_type(["dnf5", "install", "package"]) == "dnf"

    def test_bash_returns_script(self):
        assert _detect_source_type(["bash", "-c", "echo hello"]) == "script"

    def test_epm_returns_apt(self):
        assert _detect_source_type(["epm", "-i", "package"]) == "apt"

    def test_apt_get_returns_apt(self):
        assert _detect_source_type(["apt-get", "install", "package"]) == "apt"


class TestExtractPkgNames:
    def test_simple_packages(self):
        assert _extract_pkg_names(["dnf", "install", "pkg1", "pkg2"]) == ["pkg1", "pkg2"]

    def test_skips_flags(self):
        assert _extract_pkg_names(["dnf", "install", "-y", "pkg1", "--assumeno", "pkg2"]) == ["pkg1", "pkg2"]

    def test_empty_with_only_flags(self):
        assert _extract_pkg_names(["dnf", "install", "-y"]) == []


class TestParseDnfOutput:
    def test_english_install_output(self):
        lines = [
            "================================================\n",
            " Package    Arch   Version      Repository  Size\n",
            "================================================\n",
            "Installing:\n",
            " gcc        x86_64 14.2.1-1.fc41 fedora     12 M\n",
            "\n",
            "Transaction Summary\n",
            "================================================\n",
            "Install  1 Package\n",
            "\n",
            "Total download size: 12 M\n",
            "Installed size: 34 M\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["gcc"], False)
        assert preview.source_type == "dnf"
        assert "gcc" in preview.new_packages
        assert not preview.upgraded_packages
        assert not preview.dry_run_failed

    def test_russian_install_output(self):
        lines = [
            "================================================\n",
            " Пакет      Арх   Версия          Репозиторий  Размер\n",
            "================================================\n",
            "Установка:\n",
            " firefox    x86_64 135.0-1.fc41   fedora       65 M\n",
            "\n",
            "Сводка транзакции\n",
            "================================================\n",
            "Установить  1 Пакет\n",
            "\n",
            "Общий размер загрузок: 65 M\n",
            "Размер установки: 180 M\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["firefox"], False)
        assert "firefox" in preview.new_packages

    def test_english_upgrade_output(self):
        lines = [
            "================================================\n",
            " Package    Arch   Version      Repository  Size\n",
            "================================================\n",
            "Upgrading:\n",
            " kernel     x86_64 6.12.0-1.fc41 updates     0\n",
            "\n",
            "Transaction Summary\n",
            "================================================\n",
            "Upgrade  1 Package\n",
            "\n",
            "Total download size: 0\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", [], False)
        assert "kernel" in preview.upgraded_packages

    def test_removing_output(self):
        lines = [
            "================================================\n",
            " Package    Arch   Version      Repository  Size\n",
            "================================================\n",
            "Removing:\n",
            " nano       x86_64 8.1-1.fc41   @System      580 k\n",
            "\n",
            "Transaction Summary\n",
            "================================================\n",
            "Remove  1 Package\n",
            "\n",
            "Installed size: 580 k\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["nano"], False)
        assert "nano" in preview.removed_packages

    def test_download_size_en(self):
        lines = [
            "Total download size: 42 M\n",
            "Installed size: 120 M\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", [], False)
        assert "42 M" in preview.download_size

    def test_download_size_ru(self):
        lines = [
            "Общий размер загрузок: 42 M\n",
            "Размер установки: 120 M\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", [], False)
        assert "42 M" in preview.download_size

    def test_errors(self):
        lines = [
            "E: Unable to locate package\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["unknown"], True)
        assert preview.errors

    def test_fallback_to_apt_parsing(self):
        lines = [
            "The following NEW packages will be installed:\n",
            "  htop\n",
            "0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n",
            "Need to get 120 kB of archives.\n",
            "After this operation, 400 kB of additional disk space will be used.\n",
        ]
        preview = _parse_dnf_output(lines, "apt", ["htop"], False)
        assert "htop" in preview.new_packages
        assert "120 kB" in preview.download_size

    def test_source_type_preserved(self):
        lines = ["Total download size: 10 M\n"]
        preview = _parse_dnf_output(lines, "dnf", ["pkg"], False)
        assert preview.source_type == "dnf"

    def test_package_names_preserved(self):
        lines = ["Total download size: 10 M\n"]
        preview = _parse_dnf_output(lines, "dnf", ["pkg1", "pkg2"], False)
        assert preview.package_names == ["pkg1", "pkg2"]

    def test_dry_run_failed(self):
        preview = _parse_dnf_output([], "dnf", ["pkg"], True)
        assert preview.dry_run_failed is True


class TestGetInstallPreview:
    def test_flatpak_source(self):
        preview = get_install_preview(["flatpak", "install", "flathub", "org.gimp.GIMP"])
        assert preview.source_type == "flatpak"

    def test_script_source(self):
        preview = get_install_preview(["bash", "-c", "echo hi"])
        assert preview.source_type == "script"

    def test_dist_upgrade_dry_cmd(self):
        preview = InstallPreview(source_type="dnf", dry_run_failed=True)
        preview = get_install_preview(["dnf", "upgrade"])
        assert preview.source_type == "dnf"

    def test_distro_sync_is_dist_upgrade(self):
        preview = get_install_preview(["dnf", "distro-sync"])
        assert preview.source_type == "dnf"

    def test_install_preview_with_packages(self):
        preview = InstallPreview(source_type="dnf", dry_run_failed=True)
        preview = get_install_preview(["dnf", "install", "htop"])
        assert preview.source_type == "dnf"
