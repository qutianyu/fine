"""
Data Cache Module - Unified caching for market data

Supports multiple cache backends:
- CSV: File-based CSV storage
- SQLite: SQLite database storage
- Memory: In-memory cache (for testing)

Usage:
    cache = get_cache("csv", cache_dir="./cache")
    cache = get_cache("sqlite", cache_dir="./cache")
    cache = get_cache("memory")
"""

import csv
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class CacheBase(ABC):
    """Cache base class"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cached value"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass

    def get_kline(self, symbol: str, period: str = "daily") -> Optional[Any]:
        """Get kline data"""
        return self.get(f"kline:{symbol}:{period}")

    def set_kline(self, symbol: str, data: Any, period: str = "daily", 
                  ttl: int = 3600) -> None:
        """Set kline data"""
        self.set(f"kline:{symbol}:{period}", data, ttl)


@dataclass
class CacheStats:
    """Cache statistics"""
    total_keys: int = 0
    expired_keys: int = 0
    disk_size: int = 0


class CSVCache(CacheBase):
    """CSV file-based cache

    Usage:
        cache = CSVCache(cache_dir=".fine_cache")
        cache.set("key", {"data": "value"}, ttl=3600)
        value = cache.get("key")
    """

    def __init__(self, cache_dir: str = ".fine_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.cache_dir / "cache_meta.json"
        self._meta: Dict[str, Dict[str, Any]] = self._load_meta()

    def _load_meta(self) -> Dict[str, Dict[str, Any]]:
        if self.meta_file.exists():
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_meta(self) -> None:
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False, indent=2)

    def _get_cache_path(self, key: str) -> Path:
        safe_key = key.replace(":", "_").replace("/", "_")
        return self.cache_dir / f"{safe_key}.csv"

    def get(self, key: str) -> Optional[Any]:
        if key not in self._meta:
            return None

        meta = self._meta[key]
        if meta.get("expires_at"):
            expires_time = datetime.fromisoformat(meta["expires_at"])
            if datetime.now() > expires_time:
                self.delete(key)
                return None

        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            del self._meta[key]
            self._save_meta()
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data_type = meta.get("data_type", "json")
                if data_type == "json":
                    content = f.read()
                    return json.loads(content) if content else []
                else:
                    reader = csv.DictReader(f)
                    return list(reader)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        cache_path = self._get_cache_path(key)
        meta: Dict[str, Any] = {"created_at": datetime.now().isoformat()}

        if ttl:
            expires_at = datetime.now() + timedelta(seconds=ttl)
            meta["expires_at"] = expires_at.isoformat()

        if isinstance(value, (list, dict)):
            meta["data_type"] = "json"
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)
        else:
            meta["data_type"] = "csv"
            with open(cache_path, "w", encoding="utf-8", newline="") as f:
                if isinstance(value, list) and value:
                    writer = csv.DictWriter(f, fieldnames=value[0].keys() if hasattr(value[0], 'keys') else [])
                    writer.writeheader()
                    for row in value:
                        writer.writerow(row) if hasattr(row, 'keys') else writer.writerow(row.__dict__)

        self._meta[key] = meta
        self._save_meta()

    def delete(self, key: str) -> bool:
        if key in self._meta:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            del self._meta[key]
            self._save_meta()
            return True
        return False

    def clear(self) -> None:
        for key in list(self._meta.keys()):
            self.delete(key)

    def exists(self, key: str) -> bool:
        return key in self._meta


class SQLiteCache(CacheBase):
    """SQLite-based cache

    Usage:
        cache = SQLiteCache(cache_dir="./cache", db_name="market_data")
        cache.set("key", {"data": "value"}, ttl=3600)
        value = cache.get("key")
    """

    def __init__(self, cache_dir: str = ".fine_cache", db_name: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / f"{db_name}.sqlite"
        self._init_db()

    def _init_db(self) -> None:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
        conn.commit()
        conn.close()

    def get(self, key: str) -> Optional[Any]:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        value_json, expires_at = row
        if expires_at:
            expires_time = datetime.fromisoformat(expires_at)
            if datetime.now() > expires_time:
                self.delete(key)
                return None

        try:
            return json.loads(value_json)
        except json.JSONDecodeError:
            return value_json

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        import sqlite3
        created_at = datetime.now().isoformat()
        expires_at = None
        if ttl:
            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        value_json = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value

        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (key, value_json, created_at, expires_at)
        )
        conn.commit()
        conn.close()

    def delete(self, key: str) -> bool:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    def clear(self) -> None:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM cache")
        conn.commit()
        conn.close()

    def exists(self, key: str) -> bool:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("SELECT 1 FROM cache WHERE key = ?", (key,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists


class MemoryCache(CacheBase):
    """In-memory cache for testing"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None

        meta = self._meta.get(key, {})
        if meta.get("expires_at"):
            expires_time = datetime.fromisoformat(meta["expires_at"])
            if datetime.now() > expires_time:
                self.delete(key)
                return None

        return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        meta: Dict[str, Any] = {"created_at": datetime.now().isoformat()}
        if ttl:
            meta["expires_at"] = (datetime.now() + timedelta(seconds=ttl)).isoformat()
        self._meta[key] = meta
        self._cache[key] = value

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            if key in self._meta:
                del self._meta[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()
        self._meta.clear()

    def exists(self, key: str) -> bool:
        return key in self._cache


class CacheRegistry:
    """Cache type registry for extensibility"""
    _cache_types: Dict[str, type] = {
        "csv": CSVCache,
        "sqlite": SQLiteCache,
        "memory": MemoryCache,
    }

    @classmethod
    def register(cls, name: str, cache_class: type) -> None:
        """Register a new cache type"""
        cls._cache_types[name] = cache_class

    @classmethod
    def get(cls, name: str) -> type:
        """Get cache class by name"""
        if name not in cls._cache_types:
            raise ValueError(f"Unknown cache type: {name}. Available: {list(cls._cache_types.keys())}")
        return cls._cache_types[name]


def get_cache(cache_type: str = "memory", **kwargs) -> CacheBase:
    """Get cache instance

    Args:
        cache_type: Cache type (csv/sqlite/memory)
        **kwargs: Cache initialization parameters

    Returns:
        Cache instance

    Examples:
        cache = get_cache("memory")
        cache = get_cache("csv", cache_dir="./cache")
        cache = get_cache("sqlite", cache_dir="./cache", db_name="market_data")
    """
    cache_class = CacheRegistry.get(cache_type)
    if cache_type == "memory":
        return cache_class()
    return cache_class(**kwargs)


__all__ = [
    "CacheBase",
    "CSVCache",
    "SQLiteCache",
    "MemoryCache",
    "CacheRegistry",
    "get_cache",
]
