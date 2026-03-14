from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


KLINE_COLUMNS = [
    "symbol",      # 股票代码
    "name",        # 股票名称
    "period",      # 时间维度 (1d, 5m, etc.)
    "open",        # 开盘价
    "close",       # 最新价
    "high",        # 最高价
    "low",         # 最低价
    "volume",      # 成交量
]


class Store(ABC):
    """Data store base class"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get stored value"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set stored value"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete stored value"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all data"""
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

    @abstractmethod
    def query_klines(
        self,
        symbol: Optional[str] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Query kline data with filters"""
        pass

    @abstractmethod
    def save_kline(
        self,
        name: str,
        symbol: str,
        period: str,
        open_price: float,
        close_price: float,
        high_price: float,
        low_price: float,
        volume: int,
    ) -> None:
        """Save a single kline record"""
        pass

    @abstractmethod
    def save_klines(self, klines: List[Dict[str, Any]]) -> None:
        """Save multiple kline records"""
        pass


class StoreRegistry:
    """Store type registry for extensibility"""
    _store_types: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, store_class: type) -> None:
        """Register a new store type"""
        cls._store_types[name] = store_class

    @classmethod
    def get(cls, name: str) -> type:
        """Get store class by name"""
        if name not in cls._store_types:
            raise ValueError(f"Unknown store type: {name}. Available: {list(cls._store_types.keys())}")
        return cls._store_types[name]
