"""Тесты Фазы 2 — проверка исходного кода без импорта модулей (circular import problem)."""

from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def setup_src():
    return (SRC / "tabs" / "setup.py").read_text(encoding="utf-8")


def tweaks_src():
    return (SRC / "tabs" / "tweaks.py").read_text(encoding="utf-8")


class TestSetupPyRemovals:
    def test_sources_dir_removed(self):
        src = setup_src()
        assert "_SOURCES_DIR" not in src
        assert "_MIRRORS" not in src

    def test_detect_active_mirror_removed(self):
        assert "_detect_active_mirror" not in setup_src()

    def test_build_mirror_switch_cmd_removed(self):
        assert "_build_mirror_switch_cmd" not in setup_src()

    def test_build_mirror_menu_removed(self):
        assert "_build_mirror_menu" not in setup_src()

    def test_on_mirror_toggled_removed(self):
        assert "_on_mirror_toggled" not in setup_src()

    def test_sync_mirror_label_removed(self):
        assert "_sync_mirror_label" not in setup_src()

    def test_on_install_epm_removed(self):
        assert "_on_install_epm" not in setup_src()

    def test_on_remove_epm_removed(self):
        assert "_on_remove_epm" not in setup_src()

    def test_on_epm_uses_dnf(self):
        src = setup_src()
        assert "dnf" in src
        assert '["dnf", "upgrade", "-y"]' in src
        assert '["dnf", "makecache", "-y"]' in src
        assert "ALT Linux" not in src
        assert "epm full-upgrade" not in src

    def test_sudo_uses_usermod(self):
        src = setup_src()
        assert "usermod" not in src
        assert "gpasswd -d" not in src
        assert "control sudowheel" not in src
        assert "sudowheel enabled" not in src
        assert "_on_sudo" not in src
        assert "_r_sudo" not in src

    def test_f3d_uses_dnf(self):
        src = setup_src()
        assert '["dnf", "install", "-y", "f3d"]' in src
        assert '["dnf", "remove", "-y", "f3d"]' in src
        assert "apt-get dedup" not in src
        assert "apt-repo add task" not in src
        assert "_install_f3d_task" not in src
        assert "_ask_f3d_task_id" not in src

    def test_is_sisyphus_checks_fedora(self):
        src = setup_src()
        assert "/etc/fedora-release" in src
        assert "/etc/altlinux-release" not in src

    def test_apt_get_not_in_commands(self):
        src = setup_src()
        assert "apt-get" not in src

    def test_papirus_uses_dnf(self):
        src = setup_src()
        assert '["dnf", "install", "-y", "papirus-icon-theme"]' in src

    def test_nautilus_dnf_commands(self):
        src = setup_src()
        assert "nautilus-admin" not in src
        assert '["dnf", "install", "-y", "sushi"]' in src


class TestTweaksPyRemovals:
    def test_is_sisyphus_function_removed(self):
        src = tweaks_src()
        assert "def _is_sisyphus()" not in src

    def test_detect_branch_function_removed(self):
        src = tweaks_src()
        assert "def _detect_branch()" not in src

    def test_build_sisyphus_group_removed(self):
        src = tweaks_src()
        assert "def _build_sisyphus_group" not in src

    def test_build_platform_sisyphus_intro_removed(self):
        src = tweaks_src()
        assert "def _build_platform_sisyphus_intro" not in src

    def test_make_branch_badge_label_removed(self):
        src = tweaks_src()
        assert "def _make_branch_badge_label" not in src

    def test_on_check_clicked_removed(self):
        src = tweaks_src()
        assert "def _on_check_clicked" not in src

    def test_do_check_removed(self):
        src = tweaks_src()
        assert "def _do_check" not in src

    def test_check_done_error_removed(self):
        src = tweaks_src()
        assert "def _check_done_error" not in src

    def test_check_done_ok_removed(self):
        src = tweaks_src()
        assert "def _check_done_ok" not in src

    def test_on_revert_clicked_removed(self):
        src = tweaks_src()
        assert "def _on_revert_clicked" not in src

    def test_on_upgrade_clicked_removed(self):
        src = tweaks_src()
        assert "def _on_upgrade_clicked" not in src

    def test_sisyphus_badge_css_removed(self):
        src = tweaks_src()
        assert "ab-tweak-sisyphus-badge" not in src

    def test_branch_badge_css_removed(self):
        src = tweaks_src()
        assert "ab-tweak-branch-badge" not in src

    def test_sisyphus_only_badge_removed_from_add_info_row(self):
        src = tweaks_src()
        assert "sisyphus_only_badge" not in src

    def test_ananicy_uses_dnf(self):
        src = tweaks_src()
        assert "ananicy-cpp" not in src
        assert "CachyOS" not in src
        assert "apt-get" not in src

    def test_scx_scheds_uses_dnf(self):
        src = tweaks_src()
        assert "scx_lavd" not in src
        assert "scx-scheds" not in src

    def test_no_apt_get_in_tweaks(self):
        src = tweaks_src()
        assert "apt-get" not in src

    def test_no_epm_in_tweaks(self):
        src = tweaks_src()
        assert "epm " not in src

    def test_no_sisyphus_gating_in_lavd(self):
        src = tweaks_src()
        assert "is_sis = _is_sisyphus()" not in src
        assert 'sisyphus_only_badge=not is_sis' not in src
        assert 'Требуется репозиторий Sisyphus' not in src
        assert "LAVD" not in src
        assert "ananicy-cpp" not in src
        assert "CachyOS" not in src

    def test_build_ananicy_no_sisyphus_gating(self):
        src = tweaks_src()
        assert "is_sis" not in src
        assert "ananicy-cpp" not in src
        assert "CachyOS" not in src
