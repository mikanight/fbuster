"""Тесты core/borg.py — построение команд и exclude-правила."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestOptionalExcludes:
    def test_excludes_structure(self):
        from core.borg import OPTIONAL_EXCLUDES

        assert len(OPTIONAL_EXCLUDES) > 0
        for item in OPTIONAL_EXCLUDES:
            assert "key" in item
            assert "title" in item
            assert "description" in item
            assert "paths" in item
            assert isinstance(item["paths"], list)

    def test_exclude_keys_unique(self):
        from core.borg import OPTIONAL_EXCLUDES

        keys = [item["key"] for item in OPTIONAL_EXCLUDES]
        assert len(keys) == len(set(keys))

    def test_downloads_exclude(self):
        from core.borg import OPTIONAL_EXCLUDES

        downloads = next(e for e in OPTIONAL_EXCLUDES if e["key"] == "downloads")
        assert "~/Downloads" in downloads["paths"] or "~/Загрузки" in downloads["paths"]

    def test_steam_exclude(self):
        from core.borg import OPTIONAL_EXCLUDES

        steam = next(e for e in OPTIONAL_EXCLUDES if e["key"] == "steam_games")
        assert any("steamapps" in p for p in steam["paths"])

    def test_containers_exclude(self):
        from core.borg import OPTIONAL_EXCLUDES

        containers = next(e for e in OPTIONAL_EXCLUDES if e["key"] == "containers")
        assert any("containers" in p for p in containers["paths"])


class TestBorgBuildCmd:
    def test_imports(self):
        from core.borg import OPTIONAL_EXCLUDES

        assert isinstance(OPTIONAL_EXCLUDES, list)


class TestMirrorOptionalItems:
    def test_optional_items_structure(self):
        from core.mirror import OPTIONAL_ITEMS

        assert len(OPTIONAL_ITEMS) > 0
        for item in OPTIONAL_ITEMS:
            assert "key" in item
            assert "path" in item
            assert "label" in item
            assert "default" in item

    def test_optional_item_keys_unique(self):
        from core.mirror import OPTIONAL_ITEMS

        keys = [item["key"] for item in OPTIONAL_ITEMS]
        assert len(keys) == len(set(keys))


class TestMirrorAlwaysExcludes:
    def test_always_excludes_contains_essential(self):
        from core.mirror import _ALWAYS_EXCLUDES

        assert "/proc" in _ALWAYS_EXCLUDES
        assert "/sys" in _ALWAYS_EXCLUDES
        assert "/dev" in _ALWAYS_EXCLUDES
        assert "/tmp" in _ALWAYS_EXCLUDES
        assert "/run" in _ALWAYS_EXCLUDES


class TestBtrfsHelpers:
    def test_get_btrfs_mount_imports(self):
        from core.btrfs import get_btrfs_mount_for_home

        assert callable(get_btrfs_mount_for_home)

    def test_btrfs_module_imports(self):
        import core.btrfs

        assert hasattr(core.btrfs, "get_btrfs_mount_for_home")
