"""Тесты Фазы 7 — скрипты установки, rebranding инфраструктуры."""

from pathlib import Path

ROOT = Path(__file__).parent.parent


def read_file(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class TestInstallSh:
    def test_header_fedora_booster(self):
        s = read_file("install.sh")
        assert "Fedora Booster — Install Script" in s
        assert "ALT Booster" not in s

    def test_paths_use_fedorabooster(self):
        s = read_file("install.sh")
        assert "/usr/local/share/fedorabooster" in s
        assert "/usr/local/bin/fedorabooster" in s
        assert "/usr/local/share/altbooster" not in s

    def test_icon_fedorabooster(self):
        s = read_file("install.sh")
        assert "fedorabooster.svg" in s
        assert "altbooster.svg" not in s

    def test_desktop_entry_in_install_sh(self):
        s = read_file("install.sh")
        assert "Name=Fedora Booster" in s
        assert "org.fedorabooster.app" in s
        assert "Keywords=system;maintenance;clean;btrfs;trim;dnf;flatpak" in s

    def test_success_message(self):
        s = read_file("install.sh")
        assert "Fedora Booster успешно установлен" in s
        assert "fedorabooster" in s

    def test_uses_dnf_for_deps(self):
        s = read_file("install.sh")
        assert "dnf install -y" in s
        assert "apt-get" not in s

    def test_no_alt_linux_sudo_comment(self):
        s = read_file("install.sh")
        assert "На чистой установке ALT Linux sudo" not in s


class TestDesktopFile:
    def test_fedora_booster_name(self):
        s = read_file("fedorabooster.desktop")
        assert "Name=Fedora Booster" in s
        assert "ALT Booster" not in s

    def test_startup_wm_class(self):
        s = read_file("fedorabooster.desktop")
        assert "org.fedorabooster.app" in s
        assert "ru.altbooster.app" not in s

    def test_keywords_dnf_not_apt(self):
        s = read_file("fedorabooster.desktop")
        assert "dnf" in s
        assert "apt" not in s


class TestUninstallSh:
    def test_fedora_booster_references(self):
        s = read_file("uninstall.sh")
        assert "Fedora Booster" in s
        assert "ALT Booster" not in s

    def test_paths_updated(self):
        s = read_file("uninstall.sh")
        assert "/usr/local/share/fedorabooster" in s
        assert "/usr/local/bin/fedorabooster" in s


class TestShellWrapper:
    def test_exists(self):
        assert (ROOT / "fedorabooster").exists()

    def test_paths_updated(self):
        s = read_file("fedorabooster")
        assert "/usr/local/share/fedorabooster/altbooster.py" in s


class TestIconFiles:
    def test_fedorabooster_svg_exists(self):
        assert (ROOT / "icons" / "fedorabooster.svg").exists()

    def test_fedorabooster_png_exists(self):
        assert (ROOT / "icons" / "fedorabooster.png").exists()

    def test_altbooster_svg_gone(self):
        assert not (ROOT / "icons" / "altbooster.svg").exists()


class TestMakefile:
    def test_name_fedorabooster(self):
        s = read_file("Makefile")
        assert "NAME=fedorabooster" in s
