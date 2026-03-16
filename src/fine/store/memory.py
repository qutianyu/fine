from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import Store


class MemoryStore(Store):
    """内存存储，用于测试，支持结构化数据"""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._klines: List[Dict[str, Any]] = []

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None

        meta = self._meta.get(key, {})
        if meta.get("expires_at"):
            expires_time = datetime.fromisoformat(meta["expires_at"])
            if datetime.now() > expires_time:
                self.delete(key)
                return None

        return self._store[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        meta: Dict[str, Any] = {"created_at": datetime.now().isoformat()}
        if ttl:
            meta["expires_at"] = (datetime.now() + timedelta(seconds=ttl)).isoformat()
        self._meta[key] = meta
        self._store[key] = value

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            if key in self._meta:
                del self._meta[key]
            return True
        return False

    def clear(self) -> None:
        self._store.clear()
        self._meta.clear()
        self._klines.clear()

    def exists(self, key: str) -> bool:
        return key in self._store

    def query_klines(
        self,
        symbol: Optional[str] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for kline in self._klines:
            if symbol and kline.get("symbol") != symbol:
                continue
            if period and kline.get("period") != period:
                continue
            results.append(kline)

        if limit:
            results = results[:limit]
        return results

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
        kline = {
            "symbol": symbol,
            "name": name,
            "period": period,
            "open": open_price,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "volume": volume,
        }
        self._klines.append(kline)

    def save_klines(self, klines: List[Dict[str, Any]]) -> None:
        self._klines.extend(klines)

    def save_stock_info(self, stock_info: Dict[str, Any]) -> None:
        symbol = stock_info.get("symbol", "")
        if symbol:
            self._stock_info = getattr(self, "_stock_info", {})
            self._stock_info[symbol] = stock_info

    def load_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        stock_info = getattr(self, "_stock_info", {})
        return stock_info.get(symbol)
