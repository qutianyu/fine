"""
Tests for cache module.
"""

import os
import tempfile
import pytest
from market.cache import (
    CacheBase,
    MemoryCache,
    CSVCache,
    SQLiteCache,
    CacheRegistry,
    get_cache,
)


class TestMemoryCache:
    """Test MemoryCache"""

    def test_set_and_get(self):
        cache = MemoryCache()
        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")
        assert result == {"data": "value1"}

    def test_get_nonexistent(self):
        cache = MemoryCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_delete(self):
        cache = MemoryCache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent(self):
        cache = MemoryCache()
        assert cache.delete("nonexistent") is False

    def test_exists(self):
        cache = MemoryCache()
        cache.set("key1", "value1")
        assert cache.exists("key1") is True
        assert cache.exists("nonexistent") is False

    def test_clear(self):
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.exists("key1") is False
        assert cache.exists("key2") is False

    def test_ttl_expiry(self):
        cache = MemoryCache()
        cache.set("key1", "value1", ttl=-1)  # Already expired
        result = cache.get("key1")
        assert result is None

    def test_get_kline(self):
        cache = MemoryCache()
        kline_data = [{"date": "2024-01-01", "close": 100}]
        cache.set_kline("sh600519", kline_data, period="daily")
        result = cache.get_kline("sh600519", period="daily")
        assert result == kline_data


class TestCSVCache:
    """Test CSVCache"""

    def test_set_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CSVCache(cache_dir=tmpdir)
            cache.set("key1", {"data": "value1"})
            result = cache.get("key1")
            assert result == {"data": "value1"}

    def test_set_and_get_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CSVCache(cache_dir=tmpdir)
            data = [{"a": 1}, {"a": 2}, {"a": 3}]
            cache.set("key1", data)
            result = cache.get("key1")
            assert result == data

    def test_get_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CSVCache(cache_dir=tmpdir)
            result = cache.get("nonexistent")
            assert result is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CSVCache(cache_dir=tmpdir)
            cache.set("key1", "value1")
            assert cache.delete("key1") is True
            assert cache.get("key1") is None

    def test_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CSVCache(cache_dir=tmpdir)
            cache.set("key1", "value1")
            assert cache.exists("key1") is True

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CSVCache(cache_dir=tmpdir)
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            cache.clear()
            assert cache.exists("key1") is False
            assert cache.exists("key2") is False


class TestSQLiteCache:
    """Test SQLiteCache"""

    def test_set_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCache(cache_dir=tmpdir)
            cache.set("key1", {"data": "value1"})
            result = cache.get("key1")
            assert result == {"data": "value1"}

    def test_set_and_get_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCache(cache_dir=tmpdir)
            data = [{"a": 1}, {"a": 2}, {"a": 3}]
            cache.set("key1", data)
            result = cache.get("key1")
            assert result == data

    def test_get_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCache(cache_dir=tmpdir)
            result = cache.get("nonexistent")
            assert result is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCache(cache_dir=tmpdir)
            cache.set("key1", "value1")
            assert cache.delete("key1") is True
            assert cache.get("key1") is None

    def test_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCache(cache_dir=tmpdir)
            cache.set("key1", "value1")
            assert cache.exists("key1") is True

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SQLiteCache(cache_dir=tmpdir)
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            cache.clear()
            assert cache.exists("key1") is False
            assert cache.exists("key2") is False


class TestCacheRegistry:
    """Test CacheRegistry"""

    def test_get_memory(self):
        cls = CacheRegistry.get("memory")
        assert cls == MemoryCache

    def test_get_csv(self):
        cls = CacheRegistry.get("csv")
        assert cls == CSVCache

    def test_get_sqlite(self):
        cls = CacheRegistry.get("sqlite")
        assert cls == SQLiteCache

    def test_get_unknown(self):
        with pytest.raises(ValueError, match="Unknown cache type"):
            CacheRegistry.get("unknown")

    def test_register(self):
        class CustomCache(CacheBase):
            def get(self, key: str):
                return None
            def set(self, key: str, value, ttl=None):
                pass
            def delete(self, key: str) -> bool:
                return False
            def clear(self):
                pass
            def exists(self, key: str) -> bool:
                return False

        CacheRegistry.register("custom", CustomCache)
        cls = CacheRegistry.get("custom")
        assert cls == CustomCache


class TestGetCache:
    """Test get_cache function"""

    def test_get_memory_default(self):
        cache = get_cache()
        assert isinstance(cache, MemoryCache)

    def test_get_memory_explicit(self):
        cache = get_cache("memory")
        assert isinstance(cache, MemoryCache)

    def test_get_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = get_cache("csv", cache_dir=tmpdir)
            assert isinstance(cache, CSVCache)

    def test_get_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = get_cache("sqlite", cache_dir=tmpdir)
            assert isinstance(cache, SQLiteCache)

    def test_get_unknown(self):
        with pytest.raises(ValueError, match="Unknown cache type"):
            get_cache("unknown")
