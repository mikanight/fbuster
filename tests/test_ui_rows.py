"""Тесты ui/rows.py — хелперы, локальный bin, константы."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ui.rows import (
    _LOCAL_BIN_PATH_MARKER,
    _ensure_local_bin_in_shell_rc,
)


class TestLocalBinMarker:
    def test_marker_is_fedorabooster(self):
        assert "fedorabooster" in _LOCAL_BIN_PATH_MARKER
        assert "~/.local/bin" in _LOCAL_BIN_PATH_MARKER


class TestEnsureLocalBinInShellRc:
    def test_adds_block_when_marker_missing(self, tmp_path):
        log_fn = MagicMock()
        rc_path = tmp_path / ".zshrc"

        with patch("ui.rows.Path.home", return_value=tmp_path):
            with patch("os.path.exists") as mock_exists:
                mock_exists.return_value = False
                _ensure_local_bin_in_shell_rc(log_fn)

    def test_skips_when_marker_present(self, tmp_path):
        log_fn = MagicMock()
        rc_path = tmp_path / ".zshrc"
        rc_path.write_text(_LOCAL_BIN_PATH_MARKER + "\nexport PATH=$PATH:$HOME/.local/bin\n")

        with patch("ui.rows.Path.home", return_value=tmp_path):
            _ensure_local_bin_in_shell_rc(log_fn)
            content = rc_path.read_text()
            assert content.count("~/.local/bin") == 1
