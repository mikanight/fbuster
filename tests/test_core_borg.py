"""Тесты core/borg.py — borg-функции, exclude-правила, systemd-юниты."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.borg import (
    DEFAULT_EXCLUDES,
    OPTIONAL_EXCLUDES,
    _borg_env,
    _borg_exe,
    borg_estimate_create,
    borg_ssh_key_path,
    borg_version,
    disable_systemd_timer,
    enable_systemd_timer,
    flatpak_apps_from_booster_list,
    get_timer_next_run,
    is_borg_installed,
    is_repo_initialized,
    is_timer_active,
    write_systemd_units,
)


class TestBorgExe:
    def test_uses_which(self):
        with patch("shutil.which", return_value="/usr/bin/borg"):
            assert _borg_exe() == "/usr/bin/borg"

    def test_fallback_to_borgbackup(self):
        def which_side(cmd):
            if cmd == "borg":
                return None
            if cmd == "borgbackup":
                return "/usr/bin/borgbackup"
            return None
        with patch("shutil.which", side_effect=which_side):
            assert _borg_exe() == "/usr/bin/borgbackup"

    def test_fallback_to_borg_string(self):
        with patch("shutil.which", return_value=None):
            assert _borg_exe() == "borg"


class TestIsBorgInstalled:
    def test_borg_found(self):
        with patch("shutil.which", return_value="/usr/bin/borg"):
            assert is_borg_installed() is True

    def test_borg_not_found(self):
        with patch("shutil.which", return_value=None):
            assert is_borg_installed() is False

    def test_borgbackup_fallback(self):
        def which_side(cmd):
            return "/usr/bin/borgbackup" if cmd == "borgbackup" else None
        with patch("shutil.which", side_effect=which_side):
            assert is_borg_installed() is True


class TestBorgVersion:
    def test_returns_version_string(self):
        mock = MagicMock()
        mock.stdout = "borg 1.4.0\n"
        mock.returncode = 0
        with (
            patch("shutil.which", return_value="/usr/bin/borg"),
            patch("subprocess.run", return_value=mock),
        ):
            version = borg_version()
            assert version == "borg 1.4.0"

    def test_returns_none_when_not_installed(self):
        with patch("shutil.which", return_value=None):
            assert borg_version() is None

    def test_returns_none_on_error(self):
        with (
            patch("shutil.which", return_value="/usr/bin/borg"),
            patch("subprocess.run", side_effect=OSError),
        ):
            assert borg_version() is None

    def test_nonzero_return_returns_none(self):
        mock = MagicMock()
        mock.stdout = "error"
        mock.returncode = 1
        with (
            patch("shutil.which", return_value="/usr/bin/borg"),
            patch("subprocess.run", return_value=mock),
        ):
            assert borg_version() is None


class TestBorgEnv:
    def test_includes_passphrase(self, tmp_path):
        from core import config
        config.CONFIG_DIR = tmp_path
        config.STATE_FILE = tmp_path / "state.json"
        config.reset_state()
        config.state_set("borg_passphrase", "test123")

        with patch.dict(os.environ, {"HOME": str(tmp_path)}):
            with patch("core.borg.borg_ssh_key_path", return_value=tmp_path / "nonexistent"):
                env = _borg_env(str(tmp_path))
                assert env["BORG_PASSPHRASE"] == "test123"
                assert env["BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK"] == "yes"

    def test_empty_passphrase_when_not_set(self, tmp_path):
        from core import config
        config.CONFIG_DIR = tmp_path
        config.STATE_FILE = tmp_path / "state.json"
        config.reset_state()

        with patch("core.borg.borg_ssh_key_path", return_value=tmp_path / "nonexistent"):
            env = _borg_env(str(tmp_path))
            assert env["BORG_PASSPHRASE"] == ""


class TestBorgSshKeyPath:
    def test_returns_key_in_config_dir(self, tmp_path):
        from core import config
        config.CONFIG_DIR = tmp_path
        path = borg_ssh_key_path()
        assert "fedorabooster" in str(path) or "borg_id_ed25519" in str(path)


class TestIsRepoInitialized:
    def test_local_repo_detected(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README").touch()
        (repo / "config").touch()
        assert is_repo_initialized(str(repo)) is True

    def test_remote_repo_detected(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            with patch("core.borg._borg_exe", return_value="borg"):
                assert is_repo_initialized("ssh://backup@host/repo") is True

    def test_empty_path_returns_false(self):
        assert is_repo_initialized("") is False

    def test_nonexistent_path(self, tmp_path):
        repo = tmp_path / "nonexistent"
        mock = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock):
            with patch("core.borg._borg_exe", return_value="borg"):
                assert is_repo_initialized(str(repo)) is False


class TestBorgEstimateCreate:
    def test_returns_none_for_empty_repo(self):
        assert borg_estimate_create("", ["/data"], []) is None
        assert borg_estimate_create("/repo", [], []) is None


class TestSystemdUnits:
    def test_write_systemd_units_creates_files(self, tmp_path):
        from core import config
        config.SYSTEMD_USER_DIR = tmp_path

        with patch("core.borg._write_borg_env_file", return_value=True):
            ok = write_systemd_units("/tmp/borg-repo", ["/home"], "*-*-* 03:00:00")
            assert ok is True
            service = tmp_path / "fedorabooster-backup.service"
            timer = tmp_path / "fedorabooster-backup.timer"
            assert service.exists()
            assert timer.exists()
            content = service.read_text()
            assert "Fedora Booster" in content
            assert "fedorabooster-backup-meta" in content

    def test_write_systemd_units_env_file_failure(self, tmp_path):
        from core import config
        config.SYSTEMD_USER_DIR = tmp_path
        with patch("core.borg._write_borg_env_file", return_value=False):
            ok = write_systemd_units("/repo", [], "*")
            assert ok is False

    def test_write_systemd_units_permission_error(self, tmp_path):
        read_only = tmp_path / "readonly"
        read_only.mkdir(mode=0o444)
        from core import config
        config.SYSTEMD_USER_DIR = read_only
        with patch("core.borg._write_borg_env_file", return_value=True):
            try:
                ok = write_systemd_units("/repo", ["/"], "*")
            finally:
                read_only.chmod(0o755)

    def test_enable_timer_mocked(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            assert enable_systemd_timer() is True

    def test_disable_timer_mocked(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            assert disable_systemd_timer() is True

    def test_is_timer_active_mocked(self):
        mock = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock):
            assert is_timer_active() is True

    def test_is_timer_inactive_mocked(self):
        mock = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock):
            assert is_timer_active() is False

    def test_get_timer_next_run(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "NextElapseUSecRealtime=1746560000000000\n"
        with patch("subprocess.run", return_value=mock):
            result = get_timer_next_run()
            assert result is not None
            assert "." in result

    def test_get_timer_next_run_empty(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "NextElapseUSecRealtime=0\n"
        with patch("subprocess.run", return_value=mock):
            assert get_timer_next_run() is None

    def test_get_timer_next_run_error(self):
        with patch("subprocess.run", side_effect=OSError):
            assert get_timer_next_run() is None

    def test_service_content_uses_fedorabooster_units(self, tmp_path):
        from core import config
        config.SYSTEMD_USER_DIR = tmp_path
        with patch("core.borg._write_borg_env_file", return_value=True):
            write_systemd_units("/repo", ["/home"], "*")
            service = tmp_path / "fedorabooster-backup.service"
            timer = tmp_path / "fedorabooster-backup.timer"
            assert service.exists()
            assert timer.exists()
            assert "altbooster-backup" not in service.read_text()


class TestFlatpakAppsFromBoosterList:
    def test_reads_from_installed_modules(self, tmp_path):
        from core import config
        orig_conf = config.CONFIG_DIR
        try:
            config.CONFIG_DIR = tmp_path
            apps_json = tmp_path / "apps.json"
            apps_json.write_text('{"apps": [{"id": "test.app", "name": "Test"}]}')
            result = flatpak_apps_from_booster_list()
            assert isinstance(result, list)
        finally:
            config.CONFIG_DIR = orig_conf


class TestDefaultExcludes:
    def test_contains_essential_excludes(self):
        assert "~/Downloads" in DEFAULT_EXCLUDES
        assert "~/.cache" in DEFAULT_EXCLUDES
        assert "**/.git" in DEFAULT_EXCLUDES
        assert "**/node_modules" in DEFAULT_EXCLUDES
        assert "**/__pycache__" in DEFAULT_EXCLUDES
        assert "**/venv" in DEFAULT_EXCLUDES


class TestOptionalExcludesStructure:
    def test_all_have_required_keys(self):
        for item in OPTIONAL_EXCLUDES:
            assert "key" in item
            assert "title" in item
            assert "description" in item
            assert "paths" in item

    def test_keys_are_unique(self):
        keys = [e["key"] for e in OPTIONAL_EXCLUDES]
        assert len(keys) == len(set(keys))
