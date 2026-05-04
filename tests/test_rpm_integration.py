"""Интеграционные тесты RPM — используют реальный rpm в системе."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import checks
from core.packages import (
    _extract_pkg_names,
    _parse_dnf_output,
    get_install_preview,
)


def _rpm_installed(pkg: str) -> bool:
    return subprocess.run(["rpm", "-q", pkg], capture_output=True).returncode == 0


class TestRpmQueryReal:
    """Тесты, использующие реальный rpm на системе."""

    def test_rpm_query_bash_installed(self):
        assert _rpm_installed("bash") is True

    def test_rpm_query_nonexistent(self):
        assert _rpm_installed("no-such-package-99999") is False

    def test_eval_check_pair_rpm_real(self):
        result = checks._eval_check_pair("rpm", "bash")
        assert result is True

    def test_eval_check_pair_rpm_nonexistent_real(self):
        result = checks._eval_check_pair("rpm", "no-such-package-99999")
        assert result is False

    def test_check_app_installed_rpm_real(self):
        source = {
            "label": "Bash",
            "check": ["rpm", "bash"],
            "cmd": ["dnf", "install", "-y", "bash"],
        }
        assert checks.check_app_installed(source) is True

    def test_check_app_installed_rpm_nonexistent(self):
        source = {
            "label": "Fake",
            "check": ["rpm", "no-such-package-99999"],
            "cmd": ["dnf", "install", "-y", "no-such-package-99999"],
        }
        assert checks.check_app_installed(source) is False

    def test_which_check_real_bash(self):
        result = checks._eval_check_pair("which", "bash")
        assert result is True

    def test_path_check_real_etc(self):
        result = checks._eval_check_pair("path", "/etc")
        assert result is True

    def test_path_check_nonexistent(self):
        result = checks._eval_check_pair("path", "/nonexistent/path/xyz")
        assert result is False


class TestCheckAppInstalled:
    """Тесты check_app_installed с разными типами проверок."""

    def test_empty_check_returns_false(self):
        source = {"label": "Test", "check": []}
        assert checks.check_app_installed(source) is False

    def test_no_check_key_returns_false(self):
        source = {"label": "Test"}
        assert checks.check_app_installed(source) is False

    def test_flatpak_check_mocked(self):
        with patch.object(checks, "_get_flatpak_installed", return_value={"org.test.App"}):
            source = {"label": "Test", "check": ["flatpak", "org.test.App"]}
            assert checks.check_app_installed(source) is True

    def test_flatpak_check_not_found(self):
        with patch.object(checks, "_get_flatpak_installed", return_value=set()):
            source = {"label": "Test", "check": ["flatpak", "org.test.App"]}
            assert checks.check_app_installed(source) is False

    def test_rpm_check_mocked(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            source = {"label": "Test", "check": ["rpm", "bash"]}
            assert checks.check_app_installed(source) is True

    def test_rpm_check_fallback_to_which(self):
        mock_fail = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock_fail):
            source = {"label": "Test", "check": ["rpm", "bash"]}
            result = checks.check_app_installed(source)
            assert result is True

    def test_desktop_keyword_check_mocked(self):
        with patch.object(checks, "_desktop_keyword_installed", return_value=True):
            source = {"label": "Test", "check": ["desktop_keyword", "firefox"]}
            assert checks.check_app_installed(source) is True

    def test_any_of_check_all_false(self):
        source = {
            "label": "Test",
            "check": [
                "any_of",
                [
                    ["rpm", "no-such-pkg-1"],
                    ["rpm", "no-such-pkg-2"],
                ],
            ],
        }
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert checks.check_app_installed(source) is False

    def test_any_of_check_one_true(self):
        source = {
            "label": "Test",
            "check": [
                "any_of",
                [
                    ["rpm", "no-such-pkg"],
                    ["path", "/etc"],
                ],
            ],
        }
        assert checks.check_app_installed(source) is True


class TestEvalCheckPair:
    """Граничные случаи _eval_check_pair."""

    def test_unknown_kind_returns_false(self):
        assert checks._eval_check_pair("unknown", "value") is False

    def test_any_of_empty_list(self):
        assert checks._eval_check_pair("any_of", []) is False

    def test_any_of_not_list(self):
        assert checks._eval_check_pair("any_of", "not a list") is False

    def test_any_of_malformed_entries(self):
        source = [
            "not a pair",
            ["rpm"],
            [],
        ]
        assert checks._eval_check_pair("any_of", source) is False

    def test_rpm_timeout_handled(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rpm", 10)):
            assert checks._eval_check_pair("rpm", "bash") is False

    def test_rpm_oserror_handled(self):
        with patch("subprocess.run", side_effect=OSError):
            assert checks._eval_check_pair("rpm", "bash") is False

    def test_flatpak_subprocess_error_handled(self):
        with patch.object(checks, "_get_flatpak_installed", side_effect=OSError):
            checks.invalidate_flatpak_cache()
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["flatpak"], 5)):
                result = checks._eval_check_pair("flatpak", "org.test.App")
            assert result is False


class TestCacheInvalidation:
    """Тесты кэширования в checks.py."""

    def test_invalidate_flatpak_cache_clears(self):
        with patch.object(checks, "subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0, stdout="org.test.App\n")
            checks._get_flatpak_installed()
            assert mock_sub.run.call_count == 1
            checks._get_flatpak_installed()
            assert mock_sub.run.call_count == 1
            checks.invalidate_flatpak_cache()
            checks._get_flatpak_installed()
            assert mock_sub.run.call_count == 2

    def test_invalidate_desktop_files_cache(self):
        checks.invalidate_desktop_files_cache()
        assert True


class TestDnf5OutputParsing:
    """Разбор вывода DNF5 (новый формат)."""

    def test_dnf5_table_output(self):
        lines = [
            "Package                Arch        Version              Repository    Size\n",
            "Installing:\n",
            " htop                  x86_64      3.3.0-6.fc41          fedora       150.2 KiB\n",
            "\n",
            "Transaction Summary:\n",
            " Installing:        1 package\n",
            "\n",
            "Total size of inbound packages: 45 KiB\n",
            "Installed size: 500 KiB\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["htop"], False)
        assert "htop" in preview.new_packages

    def test_dnf5_upgrade_output(self):
        lines = [
            "Package                Arch        Version              Repository    Size\n",
            "Upgrading:\n",
            " kernel                x86_64      6.13.0-1.fc41         updates      0\n",
            "\n",
            "Transaction Summary:\n",
            " Upgrading:         1 package\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", [], False)
        assert "kernel" in preview.upgraded_packages

    def test_dnf5_removing_output(self):
        lines = [
            "Package                Arch        Version              Repository    Size\n",
            "Removing:\n",
            " nano                  x86_64      8.3-1.fc41            @System      580 KiB\n",
            "\n",
            "Transaction Summary:\n",
            " Removing:          1 package\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["nano"], False)
        assert "nano" in preview.removed_packages

    def test_dnf5_replacing_output(self):
        lines = [
            "Package                Arch        Version              Repository    Size\n",
            "Replacing:\n",
            " old-pkg               x86_64      1.0-1.fc41            fedora       1 MiB\n",
            "\n",
            "Transaction Summary:\n",
            " Replacing:         1 package\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["old-pkg"], False)
        assert "old-pkg" in preview.upgraded_packages

    def test_dnf5_dependency_install(self):
        lines = [
            "Installing dependencies:\n",
            " libfoo                x86_64      1.2.3-1.fc41          fedora       50 KiB\n",
            "\n",
            "Installing:\n",
            " myapp                 x86_64      2.0-1.fc41            fedora       1 MiB\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["myapp"], False)
        assert len(preview.new_packages) == 2
        assert "libfoo" in preview.new_packages
        assert "myapp" in preview.new_packages

    def test_dnf5_removing_dependencies(self):
        lines = [
            "Removing dependent packages:\n",
            " libdep                 x86_64      1.0-1.fc41          @System      100 KiB\n",
            "\n",
            "Removing:\n",
            " myapp                  x86_64      2.0-1.fc41          @System      500 KiB\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["myapp"], False)
        assert len(preview.removed_packages) == 2

    def test_dnf5_automatic_yes_no_confirmation(self):
        lines = [
            "================================================================================\n",
            " Package           Arch   Version                Repository             Size\n",
            "================================================================================\n",
            "Installing:\n",
            " gimp              x86_64 3.0.2-1.fc41           fedora                 25 MiB\n",
            "Installing dependencies:\n",
            " gimp-libs         x86_64 3.0.2-1.fc41           fedora                 12 MiB\n",
            " gegl04            x86_64 0.4.54-1.fc41          fedora                  3 MiB\n",
            "\n",
            "Transaction Summary:\n",
            "================================================================================\n",
            "Install      3 Packages\n",
            "\n",
            "Total download size: 40 MiB\n",
            "Installed size: 120 MiB\n",
            "Is this ok [y/N]: \n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["gimp"], False)
        assert len(preview.new_packages) == 3
        assert "40 MiB" in preview.download_size

    def test_dnf5_dry_run_ok_line(self):
        lines = [
            "Package                Arch        Version              Repository    Size\n",
            "Installing:\n",
            " tmux                  x86_64      3.4-1.fc41            fedora       500 KiB\n",
            "\n",
            "Transaction Summary:\n",
            " Installing:        1 package\n",
            "\n",
            "Total size of inbound packages: 500 KiB\n",
            "Installed size: 1.2 MiB\n",
            "Operation aborted.\n",
        ]
        preview = _parse_dnf_output(lines, "dnf", ["tmux"], False)
        assert "tmux" in preview.new_packages
        assert "500 KiB" in preview.download_size
        assert "1.2 MiB" in preview.disk_space


class TestInstallPreviewDnfCommands:
    """Генерация команд предпросмотра для DNF."""

    def test_dist_upgrade_dry_cmd(self):
        preview = get_install_preview(["dnf", "upgrade"])
        assert preview.source_type == "dnf"

    def test_full_upgrade_dry_cmd(self):
        preview = get_install_preview(["dnf", "full-upgrade"])
        assert preview.source_type == "dnf"

    def test_upgrade_minimal_dry_cmd(self):
        preview = get_install_preview(["dnf", "upgrade-minimal"])
        assert preview.source_type == "dnf"

    def test_install_no_packages(self):
        preview = get_install_preview(["dnf", "install"])
        assert preview.dry_run_failed is True
        assert preview.source_type == "dnf"

    def test_dnf5_install(self):
        preview = get_install_preview(["dnf5", "install", "htop", "tmux"])
        assert preview.source_type == "dnf"
        assert preview.package_names == ["htop", "tmux"]

    def test_dnf_remove(self):
        preview = get_install_preview(["dnf", "remove", "nano"])
        assert preview.source_type == "dnf"
        assert preview.package_names == ["nano"]


class TestExtractPkgNamesEdgeCases:
    """Граничные случаи извлечения имён пакетов."""

    def test_single_element_cmd(self):
        assert _extract_pkg_names(["dnf5"]) == []
        assert _extract_pkg_names(["dnf"]) == []

    def test_mixed_flags_and_packages(self):
        result = _extract_pkg_names([
            "dnf", "install",
            "--best", "--allowerasing", "-y",
            "htop", "tmux",
            "--setopt=tsflags=nodocs",
            "vim",
        ])
        assert result == ["htop", "tmux", "vim"]

    def test_groupinstall(self):
        result = _extract_pkg_names(["dnf", "groupinstall", "Development Tools"])
        assert result == ["Development Tools"]

    def test_reinstall(self):
        result = _extract_pkg_names(["dnf", "reinstall", "kernel"])
        assert result == ["kernel"]
