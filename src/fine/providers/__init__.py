"""
Market Data Providers Module
支持多种数据源: 腾讯API、新浪API、Akshare等
"""

from typing import Optional, Dict, List, Union
import numpy as np

# Base classes and dataclasses
from .base import (
    DataProvider,
    Quote,
    KLine,
    MinuteData,
    TickData,
    StockInfo,
)

# Provider implementations
from .tencent import TencentProvider
from .sina import SinaProvider
from .akshare import AkshareProvider
from .baostock import BaostockProvider
from .yfinance import YFinanceProvider
from .tushare import TushareProvider
from .efinance import EFinanceProvider
from .baidu import BaiduProvider


class ProviderRegistry:
    """数据源注册中心"""

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, provider_class: type):
        if issubclass(provider_class, DataProvider):
            cls._providers[provider_class.name] = provider_class
        return provider_class

    @classmethod
    def get(cls, name: str) -> DataProvider:
        if name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {name}. Available: {list(cls._providers.keys())}"
            )
        return cls._providers[name]()

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._providers.keys())


# Register providers
ProviderRegistry.register(TencentProvider)
ProviderRegistry.register(SinaProvider)
ProviderRegistry.register(AkshareProvider)
ProviderRegistry.register(BaostockProvider)
ProviderRegistry.register(YFinanceProvider)
ProviderRegistry.register(TushareProvider)
ProviderRegistry.register(EFinanceProvider)
ProviderRegistry.register(BaiduProvider)


class MarketData:
    """统一行情接口"""

    _store = None

    def __init__(self, provider: str = "tencent"):
        self.provider_name = provider
        self.provider: DataProvider = ProviderRegistry.get(provider)

    @classmethod
    def _get_store(cls):
        """获取或创建缓存存储"""
        if cls._store is None:
            from fine.store import StoreRegistry
            cls._store = StoreRegistry.get("csv")()
        return cls._store

    def _get_cache_key(self, symbol: str, period: str, start_date: Optional[str], end_date: Optional[str]) -> str:
        """生成缓存 key"""
        start = start_date or ""
        end = end_date or ""
        period_map = {
            "daily": "1d",
            "1d": "1d",
            "weekly": "1w",
            "1w": "1w",
            "monthly": "1M",
            "1M": "1M",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
        }
        normalized_period = period_map.get(period, period)
        return f"kline:{self.provider_name}:{symbol}:{normalized_period}:{start}:{end}"

    def _filter_by_date(self, klines: List[KLine], start_date: Optional[str], end_date: Optional[str]) -> List[KLine]:
        """按日期范围过滤 K 线"""
        if not start_date and not end_date:
            return klines

        filtered = []
        for kl in klines:
            if start_date and kl.date < start_date:
                continue
            if end_date and kl.date > end_date:
                continue
            filtered.append(kl)
        return filtered

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        cache_key = self._get_cache_key(symbol, period, start_date, end_date)
        store = self._get_store()

        cached_data = store.get(cache_key)
        if cached_data:
            klines = [KLine(**k) for k in cached_data]
            return self._filter_by_date(klines, start_date, end_date)

        klines = self.provider.get_kline(symbol, period, start_date, end_date)

        if klines:
            kline_dicts = [k.to_dict() for k in klines]
            store.set(cache_key, kline_dicts)

        return klines

    def get_kline_with_indicators(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        indicators: Optional[List[str]] = None,
    ) -> Dict:
        """获取K线数据并计算技术指标

        Args:
            symbol: 股票代码
            period: K线周期 (daily/weekly/monthly)
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            indicators: 要计算的指标列表，默认计算常用指标

        Returns:
            包含K线数据和技术指标结果的字典
        """
        from fine.indicators import compute_indicators

        klines = self.get_kline(symbol, period, start_date, end_date)

        if not klines:
            return {"klines": [], "indicators": {}}

        close = np.array([k.close for k in klines])
        high = np.array([k.high for k in klines])
        low = np.array([k.low for k in klines])
        volume = np.array([k.volume for k in klines])
        open_prices = np.array([k.open for k in klines])

        ohlcv = {
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }

        if indicators is None:
            indicators = ["ma", "ema", "macd", "kdj", "rsi", "bollingerbands", "bbi"]

        indicator_results = compute_indicators(ohlcv, indicators)

        kline_dicts = [k.to_dict() for k in klines]

        return {
            "symbol": symbol,
            "period": period,
            "klines": kline_dicts,
            "indicators": indicator_results,
        }

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        return self.provider.get_minute(symbol, date)

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return self.provider.get_hkstock(symbols)

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        return self.provider.get_stock_info(symbol)

    @classmethod
    def list_providers(cls) -> List[str]:
        return ProviderRegistry.list_providers()


def create_provider(name: str) -> DataProvider:
    """创建数据源实例"""
    return ProviderRegistry.get(name)


__all__ = [
    # Base classes
    "DataProvider",
    "Quote",
    "KLine",
    "MinuteData",
    "TickData",
    "StockInfo",
    # Providers
    "TencentProvider",
    "SinaProvider",
    "AkshareProvider",
    "BaostockProvider",
    "YFinanceProvider",
    "TushareProvider",
    "EFinanceProvider",
    "BaiduProvider",
    # Registry & Market
    "ProviderRegistry",
    "MarketData",
    "create_provider",
]
