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


class MarketData:
    """统一行情接口"""

    MAJOR_INDEXES = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
        "sh000300": "沪深300",
        "sh000016": "上证50",
        "sz399005": "中小板指",
        "sh000905": "中证500",
        "sh000688": "科创50",
    }

    def __init__(self, provider: str = "tencent"):
        self.provider_name = provider
        self.provider: DataProvider = ProviderRegistry.get(provider)

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        return self.provider.get_quote(symbols)

    def get_index(
        self, symbol: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return self.provider.get_index(symbol)

    def get_stock(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        return self.provider.get_quote(symbols)

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        return self.provider.get_etf(symbols)

    def get_all_stocks(self) -> List[Quote]:
        return self.provider.get_all_stocks()

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        return self.provider.get_kline(symbol, period, start_date, end_date)

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
        from fine.market_data.indicators import compute_indicators

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
    # Registry & Market
    "ProviderRegistry",
    "MarketData",
    "create_provider",
]
