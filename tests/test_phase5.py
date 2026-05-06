"""Тесты Фазы 5 — rebranding (ALT Booster → Fedora Booster), удаление EPM/Sisyphus из UI."""

from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def read_file(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


class TestAppBrand:
    def test_application_id(self):
        s = read_file("altbooster.py")
        assert "org.fedorabooster.app" in s
        assert "ru.altbooster.app" not in s

    def test_app_class_renamed(self):
        s = read_file("altbooster.py")
        assert "FedoraBoosterApp" in s
        assert "AltBoosterApp" not in s

    def test_help_text(self):
        s = read_file("altbooster.py")
        assert "fedorabooster" in s


class TestWindowBrand:
    def test_window_class_renamed(self):
        s = read_file("ui/window.py")
        assert "FedoraBoosterWindow" in s
        assert "AltBoosterWindow" not in s

    def test_window_title(self):
        s = read_file("ui/window.py")
        assert "Fedora Booster" in s
        assert "ALT Booster" not in s

    def test_no_alt_workstation_icon(self):
        s = read_file("ui/window.py")
        assert "alt-workstation" not in s

    def test_fedora_guide_url(self):
        s = read_file("ui/window.py")
        assert "_FEDORA_BOOSTER_GUIDE_URL" not in s
        assert "_ALT_ZERO_GUIDE_URL" not in s

    def test_init_references_fedora_booster_window(self):
        s = read_file("ui/__init__.py")
        assert "FedoraBoosterWindow" in s
        assert "AltBoosterWindow" not in s


class TestGlobalSearch:
    def test_no_eepm_in_search(self):
        s = read_file("ui/global_search.py")
        assert "eepm" not in s

    def test_no_sudowheel_in_search(self):
        s = read_file("ui/global_search.py")
        assert "sudowheel" not in s

    def test_no_sisyphus_in_search(self):
        s = read_file("ui/global_search.py")
        assert "sisyphus" not in s

    def test_no_epm_install_item(self):
        s = read_file("ui/global_search.py")
        assert "Установить EPM" not in s

    def test_fedora_in_base_keywords(self):
        s = read_file("ui/global_search.py")
        assert '"fedora"' in s


class TestAppBranchNames:
    def test_fedora_branch_in_combo(self):
        s = read_file("tabs/apps.py")
        assert '"Fedora"' in s
        assert '"Sisyphus"' not in s

    def test_rpmfusion_in_combo(self):
        s = read_file("tabs/apps.py")
        assert '"RPM Fusion"' in s

    def test_branch_map_fedora(self):
        s = read_file("tabs/apps.py")
        assert '"fedora"' in s
        assert '"sisyphus"' not in s
        assert '"p11"' not in s

    def test_no_epm_play_in_branch_map(self):
        s = read_file("tabs/apps.py")
        assert 'EPM Play' not in s  # UI label
        assert '"epm play"' not in s  # combo model string
        assert 'branch_map = {0: "fedora"' in s


class TestTweakBrand:
    def test_scheduler_is_in_tabs(self):
        s = read_file("ui/window.py")
        assert '"scheduler"' in s
        assert 'SchedulerPage' in s


class TestBorgEpmFix:
    def test_borg_uses_dnf_not_epm(self):
        s = read_file("core/borg.py")
        assert '"epm"' not in s
        assert '"dnf"' in s


class TestMakefile:
    def test_name_is_fedorabooster(self):
        s = (Path(__file__).parent.parent / "Makefile").read_text()
        assert "NAME=fedorabooster" in s


class TestPyproject:
    def test_name_is_fedorabooster(self):
        s = (Path(__file__).parent.parent / "pyproject.toml").read_text()
        assert "fedorabooster" in s
        assert "Fedora" in s

    def test_urls_updated(self):
        s = (Path(__file__).parent.parent / "pyproject.toml").read_text()
        assert "mikanight/fbuster" in s
