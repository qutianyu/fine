"""
Data Cache Module - CSV-based caching for market data

支持:
- K线数据缓存
- 实时行情缓存
- 自动过期清理
"""

import csv
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class CacheBase(ABC):
    """缓存基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    def get_kline(self, symbol: str, period: str = "daily") -> Optional[Any]:
        """获取K线数据"""
        return None

    def set_kline(self, symbol: str, data: Any, period: str = "daily", ttl: int = 3600) -> None:
        """设置K线数据"""
        pass


@dataclass
class CacheStats:
    """缓存统计"""

    total_keys: int = 0
    expired_keys: int = 0
    disk_size: int = 0


class CSVCache(CacheBase):
    """CSV缓存实现

    Usage:
        cache = CSVCache(cache_dir=".fine_cache")

        # 缓存K线数据
        cache.set_kline("sh600519", klines, ttl=3600)

        # 获取K线数据
        klines = cache.get_kline("sh600519")

        # 清理过期数据
        cache.cleanup_expired()
    """

    def __init__(self, cache_dir: str = ".fine_cache"):
        """初始化缓存

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 元数据文件
        self.meta_file = self.cache_dir / "cache_meta.json"
        self._meta: Dict[str, Dict[str, Any]] = self._load_meta()

    def _load_meta(self) -> Dict[str, Dict[str, Any]]:
        """加载元数据"""
        if self.meta_file.exists():
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_meta(self) -> None:
        """保存元数据"""
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False, indent=2)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 将key转换为安全的文件名
        safe_key = key.replace(":", "_").replace("/", "_")
        return self.cache_dir / f"{safe_key}.csv"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._meta:
            return None

        meta = self._meta[key]

        # 检查是否过期
        if meta.get("expires_at"):
            expires_time = datetime.fromisoformat(meta["expires_at"])
            if datetime.now() > expires_time:
                self.delete(key)
                return None

        # 读取CSV文件
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            del self._meta[key]
            self._save_meta()
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                # 根据data_type反序列化
                data_type = meta.get("data_type", "json")
                
                if data_type == "json":
                    # JSON数据从文件读取
                    content = f.read()
                    return json.loads(content) if content else []
                else:
                    # CSV数据从DictReader读取
                    reader = csv.DictReader(f)
                    return list(reader)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        expires_at = None
        if ttl:
            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        # 保存数据到CSV
        cache_path = self._get_cache_path(key)

        try:
            if isinstance(value, list) and len(value) > 0:
                # 如果是字典列表，保存为CSV
                if isinstance(value[0], dict):
                    with open(cache_path, "w", encoding="utf-8", newline="") as f:
                        if value:
                            writer = csv.DictWriter(f, fieldnames=value[0].keys())
                            writer.writeheader()
                            writer.writerows(value)
                    
                    self._meta[key] = {
                        "created_at": datetime.now().isoformat(),
                        "expires_at": expires_at,
                        "data_type": "list",
                        "rows": len(value),
                    }
                else:
                    # 其他列表保存为JSON
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(value, f, ensure_ascii=False)
                    
                    self._meta[key] = {
                        "created_at": datetime.now().isoformat(),
                        "expires_at": expires_at,
                        "data_type": "json",
                    }
            else:
                # 其他数据保存为JSON
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(value, f, ensure_ascii=False, default=str)
                
                self._meta[key] = {
                    "created_at": datetime.now().isoformat(),
                    "expires_at": expires_at,
                    "data_type": "json",
                }

            self._save_meta()
        except Exception as e:
            print(f"Cache set error: {e}")

    def delete(self, key: str) -> bool:
        """删除缓存"""
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()

        if key in self._meta:
            del self._meta[key]
            self._save_meta()
            return True

        return False

    def clear(self) -> None:
        """清空缓存"""
        for key in list(self._meta.keys()):
            self.delete(key)

    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        now = datetime.now()
        deleted = 0

        for key, meta in list(self._meta.items()):
            if meta.get("expires_at"):
                expires_time = datetime.fromisoformat(meta["expires_at"])
                if now > expires_time:
                    self.delete(key)
                    deleted += 1

        return deleted

    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        total_keys = len(self._meta)
        expired_keys = 0
        disk_size = 0

        now = datetime.now()

        for key, meta in self._meta.items():
            # 检查过期
            if meta.get("expires_at"):
                expires_time = datetime.fromisoformat(meta["expires_at"])
                if now > expires_time:
                    expired_keys += 1

            # 计算磁盘大小
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                disk_size += cache_path.stat().st_size

        return CacheStats(
            total_keys=total_keys,
            expired_keys=expired_keys,
            disk_size=disk_size,
        )

    # ============ 便捷方法 ============

    def set_kline(
        self,
        symbol: str,
        klines: List[Any],
        period: str = "daily",
        ttl: int = 3600,
    ) -> None:
        """缓存K线数据

        Args:
            symbol: 股票代码
            klines: K线数据列表
            period: 周期
            ttl: 过期时间(秒)
        """
        key = f"kline:{symbol}:{period}"
        
        # 转换为字典列表
        data = []
        for kline in klines:
            if hasattr(kline, "to_dict"):
                data.append(kline.to_dict())
            elif isinstance(kline, dict):
                data.append(kline)
        
        self.set(key, data, ttl)

    def get_kline(self, symbol: str, period: str = "daily") -> Optional[List[Dict]]:
        """获取K线数据

        Args:
            symbol: 股票代码
            period: 周期

        Returns:
            K线数据列表
        """
        key = f"kline:{symbol}:{period}"
        return self.get(key)

    def set_quote(self, symbol: str, quote: Dict[str, Any], ttl: int = 60) -> None:
        """缓存实时行情

        Args:
            symbol: 股票代码
            quote: 行情数据
            ttl: 过期时间(秒)
        """
        key = f"quote:{symbol}"
        self.set(key, quote, ttl)

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取实时行情

        Args:
            symbol: 股票代码

        Returns:
            行情数据
        """
        key = f"quote:{symbol}"
        return self.get(key)

    def set_indicator(
        self,
        symbol: str,
        indicator_name: str,
        data: Any,
        ttl: int = 3600,
    ) -> None:
        """缓存指标数据

        Args:
            symbol: 股票代码
            indicator_name: 指标名称
            data: 指标数据
            ttl: 过期时间(秒)
        """
        key = f"indicator:{symbol}:{indicator_name}"
        self.set(key, data, ttl)

    def get_indicator(self, symbol: str, indicator_name: str) -> Optional[Any]:
        """获取指标数据

        Args:
            symbol: 股票代码
            indicator_name: 指标名称

        Returns:
            指标数据
        """
        key = f"indicator:{symbol}:{indicator_name}"
        return self.get(key)


class MemoryCache(CacheBase):
    """内存缓存实现 (用于测试或小数据量)"""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]

        # 检查是否过期
        if expires_at and datetime.now() > expires_at:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        expires_at = None
        if ttl:
            expires_at = datetime.now() + timedelta(seconds=ttl)

        self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()


# ============ 便捷函数 ============


def get_cache(cache_type: str = "csv", **kwargs) -> CacheBase:
    """获取缓存实例

    Args:
        cache_type: 缓存类型 (csv/memory)
        **kwargs: 缓存初始化参数

    Returns:
        缓存实例
    """
    if cache_type == "csv":
        return CSVCache(kwargs.get("cache_dir", ".fine_cache"))
    elif cache_type == "memory":
        return MemoryCache()
    else:
        raise ValueError(f"Unknown cache type: {cache_type}")
