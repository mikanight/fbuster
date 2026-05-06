"""Расширенные тесты core/config.py — DNF lock, systemd, debounce, debug."""

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import config


class TestIsBtrfs:
    def test_btrfs_detected(self):
        mock = MagicMock()
        mock.stdout = "/home\n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            assert config.is_btrfs() is True

    def test_btrfs_not_detected(self):
        mock = MagicMock()
        mock.stdout = ""
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            assert config.is_btrfs() is False

    def test_btrfs_error(self):
        with patch("subprocess.run", side_effect=OSError):
            assert config.is_btrfs() is False


class TestDebugMode:
    def test_debug_default(self):
        config.init_runtime()
        assert config.DEBUG is False

    def test_debug_enabled(self):
        config.init_runtime(debug=True)
        assert config.DEBUG is True

    def test_debug_disabled(self):
        config.init_runtime(debug=False)
        assert config.DEBUG is False


class TestInitialTab:
    def test_initial_tab_empty_by_default(self):
        config.init_runtime()
        assert config.INITIAL_TAB == ""

    def test_initial_tab_set(self):
        config.init_runtime(initial_tab="setup")
        assert config.INITIAL_TAB == "setup"


class TestLogException:
    def test_logs_when_debug(self):
        config.init_runtime(debug=True)
        with patch("builtins.print") as mock_print:
            config.log_exception("test error")
            mock_print.assert_called()

    def test_silent_when_not_debug(self):
        config.init_runtime(debug=False)
        with patch("builtins.print") as mock_print:
            config.log_exception("test error")
            mock_print.assert_not_called()


class TestStateDebounce:
    def test_flush_ensures_persistence(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("debounce_test", 123)
        config.flush_pending_state()

        import json
        data = json.loads(config.STATE_FILE.read_text())
        assert data.get("debounce_test") == 123

    def test_reset_clears_all(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("k1", "v1")
        config.state_set("k2", "v2")
        config.reset_state()
        assert config.state_get("k1") is None
        assert config.state_get("k2") is None


class TestGetStateCopy:
    def test_copy_is_independent(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("original", "value")
        copy = config.get_state_copy()
        assert copy["original"] == "value"
        copy["original"] = "modified"
        assert config.state_get("original") == "value"


class TestVersion:
    def test_version_is_string(self):
        assert isinstance(config.VERSION, str)
        assert len(config.VERSION) > 0

    def test_version_has_dot_separators(self):
        assert "." in config.VERSION


class TestGsettingsConstants:
    def test_mutter_schema(self):
        assert config.GSETTINGS_MUTTER == "org.gnome.mutter"

    def test_keybindings_schema(self):
        assert config.GSETTINGS_KEYBINDINGS == "org.gnome.desktop.wm.keybindings"


class TestSystemdUserDir:
    def test_path_structure(self):
        assert ".config" in str(config.SYSTEMD_USER_DIR)
        assert "systemd" in str(config.SYSTEMD_USER_DIR)
        assert "user" in str(config.SYSTEMD_USER_DIR)


class TestDvCacheAndProxy:
    def test_dv_cache_default(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()
        assert config.get_dv_cache() == ""

    def test_dv_proxy_default(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()
        assert config.get_dv_proxy() == ""
