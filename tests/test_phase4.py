"""Тесты Фазы 4 — системные команды и пути (update-grub → grub2-mkconfig, apt-get cleanups)."""

from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def read_file(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


def read_install_sh() -> str:
    return (Path(__file__).parent.parent / "install.sh").read_text(encoding="utf-8")


class TestUpdateGrubReplaced:
    def test_mirror_py_no_update_grub(self):
        s = read_file("core/mirror.py")
        assert "update-grub" not in s
        assert "grub2-mkconfig" in s
        assert "/boot/grub2/grub.cfg" in s

    def test_amd_json_no_update_grub(self):
        s = read_file("modules/amd.json")
        assert "update-grub" not in s

    def test_amd_py_no_update_grub(self):
        s = read_file("tabs/amd.py")
        assert "update-grub" not in s

    def test_terminal_py_grub2_mkconfig(self):
        s = read_file("tabs/terminal.py")
        assert "grub-mkconfig" not in s

    def test_terminal_actions_py_grub2_mkconfig(self):
        s = read_file("tabs/terminal_actions.py")
        assert "grub2-mkconfig" in s


class TestAptGetCleanups:
    def test_rows_py_uses_dnf_makecache(self):
        s = read_file("ui/rows.py")
        assert "apt-get" not in s
        assert "dnf makecache" in s

    def test_extensions_py_uses_dnf(self):
        s = read_file("tabs/extensions.py")
        assert "apt-get install" not in s
        assert "python3-pip" in s

    def test_privileges_py_apt_error_hint_replaced(self):
        s = read_file("core/privileges.py")
        assert "You may want to run apt-get update to correct" not in s
        assert "_apt_dedup_filter" not in s


class TestPaths:
    def test_setup_py_fedora_release(self):
        s = read_file("tabs/setup.py")
        assert "/etc/fedora-release" in s
