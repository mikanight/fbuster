"""Тесты Фазы 6 — каталог расширений GNOME Shell (20 расширений, удаление EPM, GitHub)."""

from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def read_file(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


class TestExtensionsCatalog:
    def src(self):
        return read_file("tabs/extensions.py")

    def test_recommended_kept_5(self):
        s = self.src()
        assert "appindicatorsupport@rgcjonas.gmail.com" in s
        assert "Vitals@CoreCoding.com" in s
        assert "just-perfection-desktop@just-perfection" in s
        assert "blur-my-shell@aunetx" in s
        assert "right-click-next@derVedro" in s

    def test_old_8_removed(self):
        s = self.src()
        removed = [
            "dash-to-dock@micxgx.gmail.com",
            "dash-to-panel@jderose9.github.com",
            "pigeon@subz69.github",
            "auto-accent-colour@Wartybix",
            "rounded-window-corners@fxgn",
            "ding@rastersoft.com",
            "no-overview@fthx",
            "status-tray@keithvassallo.com",
        ]
        for uuid in removed:
            assert uuid not in s, f"{uuid} must be removed"

    def test_new_11_included(self):
        s = self.src()
        new_exts = [
            "caffeine@patapon.info",
            "clipboard-indicator@tudmotu.com",
            "compiz-alike-magic-lamp-effect@hermes83.github.com",
            "date-menu-formatter@marcinjakubowski.github.com",
            "status-area-horizontal-spacing@mathematical.coffee.gmail.com",
            "tilingshell@ferrarodomenico.com",
            "tweaks-system-menu@extensions.gnome-shell.fifi.org",
            "weatherornot@somepaulo.github.io",
            "windowIsReady_Remover@nunofarruca@gmail.com",
            "advanced-weather@sanjai.com",
            "transcode-appsearch@k.kubusha@gmail.com",
        ]
        for uuid in new_exts:
            assert uuid in s, f"New extension {uuid} missing"

    def test_github_extensions_included(self):
        s = self.src()
        assert "zorkiy@toxblh.ru" not in s
        assert "github:https://github.com/Toxblh/gnome-shell-extension-zorkiy" not in s
        assert "icon-matcher" not in s

    def test_epm_install_removed(self):
        s = self.src()
        assert 'install_id.startswith("epm:")' not in s
        assert 'backend.run_epm(["epm", "-i", "-y", pkg]' not in s

    def test_github_install_method_exists(self):
        s = self.src()
        assert "_install_from_github" in s

    def test_find_extension_dir_exists(self):
        s = self.src()
        assert "_find_extension_dir" in s


class TestGlobalSearchExtensions:
    def test_no_old_ext_in_keywords(self):
        s = read_file("ui/global_search.py")
        assert "dash-to-dock" not in s
        assert "dash-to-panel" not in s
