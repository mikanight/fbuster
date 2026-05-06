"""Тесты Фазы 3 — проверка названий пакетов ALT → Fedora."""

from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def read_file(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


def read_install_sh() -> str:
    return (Path(__file__).parent.parent / "install.sh").read_text(encoding="utf-8")


class TestDavinciPackages:
    def src(self):
        return read_file("tabs/davinci.py")

    def test_rocm_packages_replaced(self):
        s = self.src()
        assert "rocm-opencl" in s
        assert "rocm-hip" in s
        assert "mesa-libGLU" in s
        assert "ffmpeg-free" in s
        assert "rocm-opencl-runtime" not in s
        assert "hip-runtime-amd" not in s

    def test_fairlight_uses_alsa_plugins_pulseaudio(self):
        s = self.src()
        assert "alsa-plugins-pulseaudio" in s

    def test_rocm_uses_dnf(self):
        s = self.src()
        assert '["dnf", "install", "-y"' in s


class TestFlatpakPackages:
    def src(self):
        return read_file("tabs/flatpak.py")

    def test_flatpak_repo_flathub_removed(self):
        s = self.src()
        assert "flatpak-repo-flathub" not in s

    def test_uses_flatpak_remote_add(self):
        s = self.src()
        assert "remote-add" in s
        assert "flathub.flatpakrepo" in s

    def test_no_apt_get(self):
        s = self.src()
        assert "apt-get" not in s




class TestIntelPackages:
    def src(self):
        return read_file("tabs/intel.py")

    def test_uses_dnf_for_deps(self):
        s = self.src()
        assert '["dnf", "install", "-y", "rust", "cargo", "git", "clang", "llvm"]' in s


class TestTerminalPython:
    def src(self):
        return read_file("tabs/terminal.py")

    def test_fira_code_fonts(self):
        s = self.src()
        assert "fira-code-fonts" in s
        assert "fonts-ttf-fira-code-nerd" not in s

    def test_no_epm_commands(self):
        s = self.src()
        assert "epm " not in s

    def test_no_apt_get(self):
        s = self.src()
        assert "apt-get" not in s

    def test_ep_aliases_removed(self):
        s = self.src()
        assert "epm-help" not in s
        assert "epmqp" not in s
        assert "epms" not in s

    def test_dnf_upgrade_alias(self):
        s = self.src()
        assert "sudo dnf upgrade -y" not in s
        assert "dnf clean all" not in s


class TestTerminalActions:
    def src(self):
        return read_file("tabs/terminal_actions.py")

    def test_dnf_aliases(self):
        s = self.src()
        assert "sudo dnf upgrade -y" in s
        assert "sudo dnf clean all" in s

    def test_grub2_aliases(self):
        s = self.src()
        assert "grub2-mkconfig -o /boot/grub2/grub.cfg" in s
        assert "update-grub" not in s


class TestBorgInstall:
    def src(self):
        return read_file("tabs/timesync/page.py")

    def test_borgbackup_package(self):
        s = self.src()
        assert "borgbackup" in s

    def test_no_epm_install_borg(self):
        s = self.src()
        assert '["epm", "install", "-y", "borg"]' not in s


class TestInstallSh:
    def src(self):
        return read_install_sh()

    def test_python3_gobject(self):
        s = self.src()
        assert "python3-gobject" in s
        assert "gtk4" in s
        assert "python3-module-pygobject3" not in s
        assert "libgtk4-gir" not in s

    def test_libadwaita(self):
        s = self.src()
        assert "libadwaita" in s
        assert "libadwaita-gir" not in s

    def test_uses_dnf(self):
        s = self.src()
        assert "dnf install -y" in s
        assert "apt-get install" not in s


class TestJsonModules:
    def test_maintenance_json_dnf(self):
        s = read_file("modules/maintenance.json")
        assert '"dnf"' in s
        assert '"apt-get"' not in s

    def test_terminal_json_dnf(self):
        s = read_file("modules/terminal.json")
        assert '"dnf"' in s
        assert '"apt-get"' not in s
        assert "fira-code-fonts" in s

    def test_apps_json_dnf(self):
        s = read_file("modules/apps.json")
        assert '"dnf"' in s
        assert '"apt-get"' not in s
