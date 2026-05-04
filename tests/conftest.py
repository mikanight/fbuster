"""Mock Gtk/GLib for tests running on macOS (no Gtk available)."""

import sys
from unittest.mock import MagicMock

mock_gi = MagicMock()
mock_gi.repository.GLib.idle_add = MagicMock()
mock_gi.repository.Adw = MagicMock()
mock_gi.repository.Gtk = MagicMock()

sys.modules["gi"] = mock_gi
sys.modules["gi.repository"] = mock_gi.repository
sys.modules["gi.repository.GLib"] = mock_gi.repository.GLib
sys.modules["gi.repository.Adw"] = mock_gi.repository.Adw
sys.modules["gi.repository.Gtk"] = mock_gi.repository.Gtk
