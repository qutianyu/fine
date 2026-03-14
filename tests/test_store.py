import pytest
import tempfile
import os
from pathlib import Path


class TestCSVStore:
    def test_set_and_get(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            key = "test_key"
            value = {"name": "test", "value": 123}

            store.set(key, value)
            result = store.get(key)

            assert result == value

    def test_get_nonexistent(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            result = store.get("nonexistent")
            assert result is None

    def test_exists(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            key = "test_key"
            value = {"data": "test"}

            assert store.exists(key) is False
            store.set(key, value)
            assert store.exists(key) is True

    def test_delete(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            key = "test_key"
            value = {"data": "test"}

            store.set(key, value)
            assert store.exists(key) is True

            store.delete(key)
            assert store.exists(key) is False

    def test_clear(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            store.set("key1", {"data": "1"})
            store.set("key2", {"data": "2"})

            store.clear()

            assert store.get("key1") is None
            assert store.get("key2") is None

    def test_kline_cache_filename(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            key = "kline:baostock:sh600519:1d:2024-01-01:2024-01-31"
            value = [{"date": "2024-01-01", "close": 100}]

            store.set(key, value)

            expected_file = Path(tmpdir) / "sh600519_1d_2024-01-01_2024-01-31.csv"
            assert expected_file.exists()

            result = store.get(key)
            assert result == value


class TestMemoryStore:
    def test_set_and_get(self):
        from fine.store import MemoryStore

        store = MemoryStore()

        key = "test_key"
        value = {"name": "test", "value": 123}

        store.set(key, value)
        result = store.get(key)

        assert result == value

    def test_exists(self):
        from fine.store import MemoryStore

        store = MemoryStore()

        key = "test_key"
        value = {"data": "test"}

        assert store.exists(key) is False
        store.set(key, value)
        assert store.exists(key) is True

    def test_delete(self):
        from fine.store import MemoryStore

        store = MemoryStore()

        key = "test_key"
        value = {"data": "test"}

        store.set(key, value)
        store.delete(key)

        assert store.exists(key) is False

    def test_clear(self):
        from fine.store import MemoryStore

        store = MemoryStore()

        store.set("key1", {"data": "1"})
        store.set("key2", {"data": "2"})

        store.clear()

        assert store.get("key1") is None
        assert store.get("key2") is None
