"""
Market Data Providers Module
支持多种数据源: 腾讯API、新浪API、Akshare等
"""

from typing import Dict, List, Optional, Union

import numpy as np

from .akshare import AkshareProvider
from .baidu import BaiduProvider
from .baostock import BaostockProvider

# Base classes and dataclasses
from .base import (
    DataProvider,
    KLine,
    MinuteData,
    Quote,
    StockInfo,
    TickData,
)
from .eastmoney import EastmoneyProvider
from .finnhub import FinnhubProvider
from .tushare import TushareProvider

# News provider
from .news_provider import (
    AkshareNewsProvider,
    News,
    NewsProvider,
    SinaNewsProvider,
    WallstreetcnNewsProvider,
    XueqiuNewsProvider,
    YicaiNewsProvider,
    get_news_provider,
    list_news_providers,
)

# Playwright scraper
from .playwright_scraper import (
    EastmoneyScraper,
    PlaywrightScraper,
    ScrapedPage,
    XueqiuScraper,
    YicaiScraper,
    create_scraper,
)
from .sina import SinaProvider

# Provider implementations
from .tencent import TencentProvider
from .yfinance import YFinanceProvider
from .netease import NetEaseProvider


class ProviderRegistry:
    """数据源注册中心"""

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, provider_class: type):
        if issubclass(provider_class, DataProvider):
            cls._providers[provider_class.name] = provider_class
        return provider_class

    @classmethod
    def get(cls, name: str, **kwargs) -> DataProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}. Available: {list(cls._providers.keys())}")
        return cls._providers[name](**kwargs)

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._providers.keys())


# Register providers
ProviderRegistry.register(TencentProvider)
ProviderRegistry.register(SinaProvider)
ProviderRegistry.register(AkshareProvider)
ProviderRegistry.register(BaostockProvider)
ProviderRegistry.register(YFinanceProvider)
ProviderRegistry.register(BaiduProvider)
ProviderRegistry.register(FinnhubProvider)
ProviderRegistry.register(EastmoneyProvider)
ProviderRegistry.register(TushareProvider)
ProviderRegistry.register(NetEaseProvider)


class MarketData:
    """统一行情接口"""

    # 支持新闻获取的 provider 列表
    _news_providers = {
        "akshare",
        "xueqiu",
        "yicai",
        "sina",
        "wallstreetcn",
        "eastmoney",
    }

    def __init__(self, provider: str = "tencent", **kwargs):
        self.provider_name = provider
        # 检查是否是新闻 provider（xueqiu, yicai 等不是数据 provider）
        if provider in self._news_providers and provider not in ProviderRegistry.list_providers():
            self.provider = None
        else:
            self.provider: DataProvider = ProviderRegistry.get(provider, **kwargs)

    def _normalize_period(self, period: str) -> str:
        """标准化period格式"""
        period_map = {
            "daily": "1d",
            "1d": "1d",
            "weekly": "1w",
            "1w": "1w",
            "monthly": "1M",
            "1M": "1M",
            "1h": "1h",
        }
        return period_map.get(period, period)

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        if self.provider is None:
            raise ValueError(
                f"Provider '{self.provider_name}' does not support get_kline. Use a data provider like akshare, baostock, yfinance, etc."
            )
        normalized_period = self._normalize_period(period)
        return self.provider.get_kline(symbol, normalized_period, start_date, end_date)

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
        if self.provider is None:
            raise ValueError(
                f"Provider '{self.provider_name}' does not support minute data. Use a data provider like akshare, baostock, yfinance, etc."
            )
        return self.provider.get_minute(symbol, date)

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if self.provider is None:
            raise ValueError(
                f"Provider '{self.provider_name}' does not support HK stock data. Use a data provider like akshare, baostock, yfinance, etc."
            )
        return self.provider.get_hkstock(symbols)

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        if self.provider is None:
            raise ValueError(
                f"Provider '{self.provider_name}' does not support stock info. Use a data provider like akshare, baostock, yfinance, etc."
            )
        return self.provider.get_stock_info(symbol)

    def get_news(
        self, symbol: Optional[str] = None, news_type: str = "efinance", fetch_content: bool = True
    ) -> List[News]:
        """获取新闻数据

        Args:
            symbol: 股票代码
            news_type: 新闻类型 ("efinance"-个股新闻, "stock"-个股新闻, "roll"-滚动新闻, "global"-全球财经, "cctv"-央视新闻, "economic"-财经日历)
            fetch_content: 是否获取完整文章内容（默认True，会增加请求时间）

        Returns:
            List[News]: 新闻数据列表
        """
        # 根据 provider 名称选择对应的新闻提供者
        news_provider_name = self.provider_name
        if news_provider_name in ("akshare", "efinance"):
            news_provider = AkshareNewsProvider()
        elif news_provider_name == "xueqiu":
            news_provider = XueqiuNewsProvider()
        elif news_provider_name == "yicai":
            news_provider = YicaiNewsProvider()
        elif news_provider_name == "sina":
            news_provider = SinaNewsProvider()
        elif news_provider_name == "wallstreetcn":
            news_provider = WallstreetcnNewsProvider()
        else:
            # 其他 provider 尝试从注册表获取
            try:
                news_provider = get_news_provider(news_provider_name)
            except ValueError:
                # 如果没有对应的新闻提供者，回退到 akshare
                news_provider = AkshareNewsProvider()

        return news_provider.get_news(symbol, news_type, fetch_content=fetch_content)

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
    # News
    "News",
    "NewsProvider",
    "get_news_provider",
    "list_news_providers",
    # Providers
    "TencentProvider",
    "SinaProvider",
    "AkshareProvider",
    "BaostockProvider",
    "YFinanceProvider",
    "EFinanceProvider",
    "BaiduProvider",
    "FinnhubProvider",
    # Registry & Market
    "ProviderRegistry",
    "MarketData",
    "create_provider",
    # Playwright Scraper
    "PlaywrightScraper",
    "XueqiuScraper",
    "YicaiScraper",
    "EastmoneyScraper",
    "ScrapedPage",
    "create_scraper",
]
