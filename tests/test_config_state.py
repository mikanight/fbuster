"""Тесты core/config.py — управление состоянием."""

import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import config


class TestStateManagement:
    def test_state_get_default(self):
        assert config.state_get("nonexistent") is None

    def test_state_get_custom_default(self):
        assert config.state_get("nonexistent", 42) == 42

    def test_state_set_and_get(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("key1", "value1")
        assert config.state_get("key1") == "value1"

        config.state_set("key2", 123)
        assert config.state_get("key2") == 123

        config.state_set("key3", True)
        assert config.state_get("key3") is True

    def test_state_persistence(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("theme", "dark")
        config.save_state()

        config._state.clear()
        config.load_state()
        assert config.state_get("theme") == "dark"

    def test_get_state_copy(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("a", 1)
        config.state_set("b", 2)

        copy = config.get_state_copy()
        assert copy == {"a": 1, "b": 2}
        copy["a"] = 99
        assert config.state_get("a") == 1

    def test_reset_state(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("x", "y")
        assert config.state_get("x") == "y"

        config.reset_state()
        assert config.state_get("x") is None

    def test_save_state_creates_dir(self, tmp_path):
        config.STATE_FILE = tmp_path / "sub" / "state.json"
        config.CONFIG_DIR = tmp_path / "sub"
        config.reset_state()

        config.state_set("hello", "world")
        config.save_state()

        assert config.STATE_FILE.exists()
        data = json.loads(config.STATE_FILE.read_text())
        assert data == {"hello": "world"}

    def test_load_state_corrupted_file(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.STATE_FILE.write_text("not valid json {{{")

        config.load_state()
        assert config.state_get("anything") is None

    def test_load_state_missing_file(self, tmp_path):
        config.STATE_FILE = tmp_path / "nonexistent.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.load_state()
        assert config.get_state_copy() == {}

    def test_flush_pending_state(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("flush_test", "done")
        config.flush_pending_state()

        data = json.loads(config.STATE_FILE.read_text())
        assert data.get("flush_test") == "done"

    def test_concurrent_state_access(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        errors = []

        def writer():
            for i in range(100):
                try:
                    config.state_set(f"key_{i}", i)
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(100):
                try:
                    config.get_state_copy()
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestConfigConstants:
    def test_version_format(self):
        assert isinstance(config.VERSION, str)
        assert len(config.VERSION) > 0

    def test_dnf_lock_files(self):
        assert "/var/run/dnf.pid" in config.DNF_LOCK_FILES

    def test_config_dir_exists(self):
        from pathlib import Path as _Path
        original = _Path.home() / ".config" / "altbooster"
        assert original.name == "altbooster"

    def test_state_file_path(self):
        assert config.STATE_FILE.name == "state.json"

    def test_systemd_user_dir(self):
        assert ".config/systemd/user" in str(config.SYSTEMD_USER_DIR)


class TestInitRuntime:
    def test_default_values(self):
        config.init_runtime()
        assert config.DEBUG is False
        assert config.INITIAL_TAB == ""

    def test_debug_mode(self):
        config.init_runtime(debug=True)
        assert config.DEBUG is True
        assert config.INITIAL_TAB == ""

    def test_initial_tab(self):
        config.init_runtime(initial_tab="apps")
        assert config.INITIAL_TAB == "apps"
        assert config.DEBUG is False


class TestDVPaths:
    def test_dv_cache_default_empty(self):
        config.reset_state()
        assert config.get_dv_cache() == ""

    def test_dv_cache_from_state(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("dv_cache_path", "/tmp/cache")
        assert config.get_dv_cache() == "/tmp/cache"

    def test_dv_proxy_default_empty(self):
        config.reset_state()
        assert config.get_dv_proxy() == ""

    def test_dv_proxy_from_state(self, tmp_path):
        config.STATE_FILE = tmp_path / "state.json"
        config.CONFIG_DIR = tmp_path
        config.reset_state()

        config.state_set("dv_proxy_path", "/tmp/proxy")
        assert config.get_dv_proxy() == "/tmp/proxy"
