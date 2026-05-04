"""Тесты core/gsettings.py — обёртки gsettings/dconf."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import gsettings


class TestRunGsettings:
    def test_success(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            assert gsettings.run_gsettings(["set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark"]) is True

    def test_failure(self):
        mock = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock):
            assert gsettings.run_gsettings(["set", "invalid.schema", "key", "value"]) is False

    def test_timeout(self):
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.TimeoutExpired(["gsettings"], 5)):
            assert gsettings.run_gsettings(["get", "schema", "key"]) is False

    def test_oserror(self):
        with patch("subprocess.run", side_effect=OSError):
            assert gsettings.run_gsettings(["get", "schema", "key"]) is False


class TestGsettingsGet:
    def test_returns_value(self):
        mock = MagicMock()
        mock.stdout = "prefer-dark\n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            result = gsettings.gsettings_get("org.gnome.desktop.interface", "color-scheme")
            assert result == "prefer-dark"

    def test_returns_empty_on_failure(self):
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.TimeoutExpired(["gsettings"], 5)):
            result = gsettings.gsettings_get("schema", "key")
            assert result == ""

    def test_returns_empty_on_oserror(self):
        with patch("subprocess.run", side_effect=OSError):
            result = gsettings.gsettings_get("schema", "key")
            assert result == ""

    def test_strips_whitespace(self):
        mock = MagicMock()
        mock.stdout = "  ['value']  \n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            result = gsettings.gsettings_get("schema", "key")
            assert result == "['value']"

    def test_boolean_value(self):
        mock = MagicMock()
        mock.stdout = "true\n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            result = gsettings.gsettings_get("org.gnome.desktop.interface", "enable-animations")
            assert result == "true"

    def test_integer_value(self):
        mock = MagicMock()
        mock.stdout = "100\n"
        mock.returncode = 0
        with patch("subprocess.run", return_value=mock):
            result = gsettings.gsettings_get("org.gnome.desktop.peripherals.mouse", "speed")
            assert result == "100"
