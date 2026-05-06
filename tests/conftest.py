"""Mock Gtk/GLib for tests and preserve config module state across tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

mock_gi = MagicMock()
mock_gi.repository.GLib.idle_add = MagicMock()
mock_gi.repository.Adw = MagicMock()
mock_gi.repository.Gtk = MagicMock()
mock_gi.repository.GdkPixbuf = MagicMock()
mock_gi.repository.Gdk = MagicMock()

sys.modules["gi"] = mock_gi
sys.modules["gi.repository"] = mock_gi.repository
sys.modules["gi.repository.GLib"] = mock_gi.repository.GLib
sys.modules["gi.repository.Adw"] = mock_gi.repository.Adw
sys.modules["gi.repository.Gtk"] = mock_gi.repository.Gtk
sys.modules["gi.repository.GdkPixbuf"] = mock_gi.repository.GdkPixbuf
sys.modules["gi.repository.Gdk"] = mock_gi.repository.Gdk

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

mock_window = MagicMock()
mock_window.FedoraBoosterWindow = MagicMock()
sys.modules["ui.window"] = mock_window

from core import config as _config_module

_ORIG_CONF_DIR = _config_module.CONFIG_DIR
_ORIG_STATE_FILE = _config_module.STATE_FILE


@pytest.fixture(autouse=True)
def _preserve_config_paths():
    _config_module.CONFIG_DIR = _ORIG_CONF_DIR
    _config_module.STATE_FILE = _ORIG_STATE_FILE
    _config_module.reset_state()
    yield
    _config_module.CONFIG_DIR = _ORIG_CONF_DIR
    _config_module.STATE_FILE = _ORIG_STATE_FILE
