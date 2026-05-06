"""Тесты модуля tabs/flatpak.py — FlatpakApp, утилиты, _build_icon_index."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tabs.flatpak import (
    FlatpakApp,
    _FLATHUB_MIRRORS,
    _build_icon_index,
    _get_flathub_url,
    _get_masked_ids,
    _is_flatpak_available,
    _list_flatpak_apps,
    _make_app_icon,
    _run_user_op,
)


class TestFlatpakAppDataclass:
    def test_default_values(self):
        app = FlatpakApp(app_id="org.test.App", name="Test App", version="1.0", installation="user")
        assert app.app_id == "org.test.App"
        assert app.name == "Test App"
        assert app.version == "1.0"
        assert app.installation == "user"
        assert app.masked is False
        assert app.icon_path is None

    def test_custom_values(self):
        app = FlatpakApp(
            app_id="org.test.App",
            name="Test",
            version="2.0",
            installation="system",
            masked=True,
            icon_path="/icons/test.png",
        )
        assert app.masked is True
        assert app.icon_path == "/icons/test.png"


class TestIsFlatpakAvailable:
    def test_flatpak_found(self):
        with patch("shutil.which", return_value="/usr/bin/flatpak"):
            assert _is_flatpak_available() is True

    def test_flatpak_not_found(self):
        with patch("shutil.which", return_value=None):
            assert _is_flatpak_available() is False


class TestListFlatpakApps:
    def test_parses_output(self):
        mock = MagicMock()
        mock.stdout = "org.gimp.GIMP\tGIMP\t2.10.38\tuser\n"
        mock.stderr = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            apps = _list_flatpak_apps()
            assert len(apps) == 1
            assert apps[0].app_id == "org.gimp.GIMP"
            assert apps[0].name == "GIMP"

    def test_incomplete_line_skipped(self):
        mock = MagicMock()
        mock.stdout = "short\norg.app\tName\t1.0\tuser\n"
        mock.stderr = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            apps = _list_flatpak_apps()
            assert len(apps) == 1

    def test_error_returns_empty(self):
        with patch("subprocess.run", side_effect=OSError):
            assert _list_flatpak_apps() == []

    def test_empty_name_uses_app_id(self):
        mock = MagicMock()
        mock.stdout = "org.test.App\t\t1.0\tuser\n"
        mock.stderr = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            apps = _list_flatpak_apps()
            assert apps[0].name == "org.test.App"


class TestGetMaskedIds:
    def test_returns_masked_set(self):
        outputs = {"--user": "org.test.app1\n", "--system": "org.test.app2\n"}
        def run_side(*args, **kwargs):
            for scope in ("--user", "--system"):
                if scope in args[0]:
                    mock = MagicMock()
                    mock.stdout = outputs[scope]
                    mock.returncode = 0
                    return mock
            return MagicMock(returncode=1)

        with patch("subprocess.run", side_effect=run_side):
            masked = _get_masked_ids()
            assert "org.test.app1" in masked
            assert "org.test.app2" in masked

    def test_handles_errors(self):
        with patch("subprocess.run", side_effect=OSError):
            assert _get_masked_ids() == set()


class TestGetFlathubUrl:
    def test_returns_url(self):
        mock = MagicMock()
        mock.stdout = "flathub\thttps://dl.flathub.org/repo/\n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            url = _get_flathub_url()
            assert "dl.flathub.org" in url

    def test_no_flathub_remote(self):
        mock = MagicMock()
        mock.stdout = "fedora\thttps://fedora.example.com/\n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            assert _get_flathub_url() is None

    def test_error_returns_none(self):
        with patch("subprocess.run", side_effect=OSError):
            assert _get_flathub_url() is None


class TestBuildIconIndex:
    def test_builds_index_from_appstream(self, tmp_path):
        base = tmp_path / "flatpak" / "appstream" / "flathub" / "x86_64" / "active" / "icons" / "64x64"
        base.mkdir(parents=True)
        (base / "org.gimp.GIMP.png").touch()
        (base / "org.gnome.Calculator.png").touch()

        with patch.object(Path, "glob", return_value=[base]):
            result = _build_icon_index()
            assert "org.gimp.GIMP" in result
            assert "org.gnome.Calculator" in result

    def test_cache_is_used(self):
        import tabs.flatpak as fm
        fm._icon_index_cache = {}
        r1 = _build_icon_index()
        r2 = _build_icon_index()
        assert r1 == r2


class TestMakeAppIcon:
    def test_returns_placeholder_when_no_path(self):
        with patch("tabs.flatpak.make_icon") as mock_icon:
            mock_icon.return_value = MagicMock()
            result = _make_app_icon(None)
            mock_icon.assert_called_once_with("package-x-generic-symbolic")

    def test_returns_pixbuf_icon(self):
        from gi.repository import Gdk, GdkPixbuf

        with (
            patch("tabs.flatpak.gi.require_version"),
            patch.object(GdkPixbuf.Pixbuf, "new_from_file_at_scale") as mock_pixbuf,
            patch.object(Gdk.Texture, "new_for_pixbuf") as mock_texture,
        ):
            mock_pixbuf.return_value = MagicMock()
            mock_texture.return_value = MagicMock()
            result = _make_app_icon("/icons/test.png")
            assert result is not None

    def test_exception_falls_back_to_generic(self):
        with patch("tabs.flatpak.make_icon") as mock_icon:
            mock_icon.return_value = MagicMock()
            with patch("tabs.flatpak.gi.require_version", side_effect=ValueError):
                result = _make_app_icon("/icons/test.png")
                mock_icon.assert_called_once()


class TestRunUserOp:
    def test_successful_operation(self):
        on_line = MagicMock()
        on_done = MagicMock()
        mock_proc = MagicMock()
        mock_proc.stdout = ["line1\n", "line2\n"]
        mock_proc.returncode = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            _run_user_op(["flatpak", "install", "app"], on_line, on_done)
            import time
            time.sleep(0.2)

    def test_exception_handling(self):
        from gi.repository import GLib
        on_line = MagicMock()
        on_done = MagicMock()

        with patch("subprocess.Popen", side_effect=OSError("test error")):
            _run_user_op(["flatpak", "install"], on_line, on_done)
            import time
            time.sleep(0.2)


class TestFlathubMirrors:
    def test_mirrors_count(self):
        assert len(_FLATHUB_MIRRORS) >= 4

    def test_default_mirror_is_official(self):
        assert _FLATHUB_MIRRORS[0][1] == "dl.flathub.org"

    def test_mirror_structure(self):
        for name, domain, url in _FLATHUB_MIRRORS:
            assert isinstance(name, str)
            assert isinstance(domain, str)
            assert isinstance(url, str)
            assert url.startswith("https://")
