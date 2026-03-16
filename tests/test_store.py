import os
import tempfile
from pathlib import Path

import pytest


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

    def test_klines_save_and_load(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            klines = [
                {"date": "2024-01-01", "symbol": "sh600519", "period": "1d", "open": 100, "close": 105, "high": 106, "low": 99, "volume": 1000000},
                {"date": "2024-01-02", "symbol": "sh600519", "period": "1d", "open": 105, "close": 110, "high": 111, "low": 104, "volume": 1100000},
            ]

            store.save_klines(klines, "sh600519", "1d")

            loaded = store.load_klines("sh600519", "1d")
            assert len(loaded) == 2
            assert loaded[0]["date"] == "2024-01-01"
            assert loaded[1]["date"] == "2024-01-02"

    def test_klines_with_date_filter(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            klines = [
                {"date": "2024-01-01", "symbol": "sh600519", "period": "1d", "open": 100, "close": 105, "high": 106, "low": 99, "volume": 1000000},
                {"date": "2024-01-15", "symbol": "sh600519", "period": "1d", "open": 105, "close": 110, "high": 111, "low": 104, "volume": 1100000},
                {"date": "2024-02-01", "symbol": "sh600519", "period": "1d", "open": 110, "close": 115, "high": 116, "low": 109, "volume": 1200000},
            ]

            store.save_klines(klines, "sh600519", "1d")

            loaded = store.load_klines("sh600519", "1d", "2024-01-10", "2024-01-31")
            assert len(loaded) == 1
            assert loaded[0]["date"] == "2024-01-15"

    def test_stock_info_save_and_load(self):
        from fine.store import CSVStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)

            info = {
                "symbol": "sh600519",
                "name": "茅台",
                "price": 1800.0,
                "pe": 30.5,
                "roe": 25.0,
            }

            store.save_stock_info(info)

            loaded = store.load_stock_info("sh600519")
            assert loaded is not None
            assert loaded["symbol"] == "sh600519"
            assert loaded["name"] == "茅台"
            assert loaded["pe"] == 30.5


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
