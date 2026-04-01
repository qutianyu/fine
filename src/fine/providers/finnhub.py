"""
Finnhub Data Provider

提供全球股票、外汇、加密货币的实时行情和历史K线数据。
免费tier有频率限制，需要API Key。

Usage:
    from fine import create_provider
    provider = create_provider("finnhub")
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import requests

from .base import DataProvider, KLine, MinuteData, Quote, StockInfo
from .utils import safe_float as _safe_float, safe_int as _safe_int


class FinnhubProvider(DataProvider):
    """Finnhub 数据Provider

    支持全球股票、外汇、加密货币的实时行情和历史K线。
    免费tier: 60 calls/minute

    Attributes:
        name: 数据源名称
        api_key: Finnhub API Key (可设置环境变量 FINNHUB_API_KEY)
    """

    name = "finnhub"

    def __init__(self, api_key: Optional[str] = None):
        """初始化Finnhub Provider

        Args:
            api_key: Finnhub API Key（必填）
        """
        if not api_key:
            raise ValueError("Finnhub API key is required. Get one at https://finnhub.io")
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self._session = requests.Session()

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        """格式化股票代码为Finnhub格式

        Args:
            symbol: 股票代码，如 AAPL, TSLA, BTC/USD

        Returns:
            Finnhub格式的代码
        """
        # 加密货币映射
        crypto_map = {
            "BTC": "BINANCE:BTCUSDT",
            "ETH": "BINANCE:ETHUSDT",
        }
        if symbol.upper() in crypto_map:
            return crypto_map[symbol.upper()]

        # 外汇映射
        forex_map = {
            "USD/CNY": "OANDA:USD_CNY",
            "EUR/USD": "OANDA:EUR_USD",
            "GBP/USD": "OANDA:GBP_USD",
        }
        if symbol.upper() in forex_map:
            return forex_map[symbol.upper()]

        # 美股直接返回（需要交易所后缀）
        if "." not in symbol:
            return symbol.upper()

        return symbol.upper()

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        """获取实时行情

        Args:
            symbols: 股票代码列表

        Returns:
            行情数据字典
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        result = {}
        for symbol in symbols:
            fmt_symbol = self._format_symbol(symbol)

            data = self._get("/quote", {"symbol": fmt_symbol})
            if not data or data.get("c") == 0:
                continue

            # 获取公司基本信息
            info = self._get("/stock/profile2", {"symbol": fmt_symbol})

            quote = Quote(
                symbol=symbol,
                name=info.get("name", symbol) if info else symbol,
                price=_safe_float(data.get("c", 0)),
                change=_safe_float(data.get("d", 0)),
                change_pct=_safe_float(data.get("dp", 0)),
                volume=_safe_int(data.get("volume", 0)),
                amount=0.0,
                open=_safe_float(data.get("o", 0)),
                high=_safe_float(data.get("h", 0)),
                low=_safe_float(data.get("l", 0)),
                prev_close=_safe_float(data.get("pc", 0)),
                source=self.name,
            )
            result[symbol] = quote

        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取指数行情

        Args:
            symbols: 指数代码列表，如 ^GSPC (S&P 500), ^DJI (道琼斯)

        Returns:
            指数行情字典
        """
        default_indices = ["^GSPC", "^DJI", "^IXIC", "^VIX"]
        symbols = symbols or default_indices

        if isinstance(symbols, str):
            symbols = [symbols]

        result = {}
        for symbol in symbols:
            # Finnhub使用特殊格式
            fmt_symbol = symbol.replace("^", "")

            data = self._get("/quote", {"symbol": fmt_symbol})
            if not data or data.get("c") == 0:
                continue

            quote = Quote(
                symbol=symbol,
                name=symbol,
                price=_safe_float(data.get("c", 0)),
                change=_safe_float(data.get("d", 0)),
                change_pct=_safe_float(data.get("dp", 0)),
                volume=0,
                amount=0.0,
                open=_safe_float(data.get("o", 0)),
                high=_safe_float(data.get("h", 0)),
                low=_safe_float(data.get("l", 0)),
                prev_close=_safe_float(data.get("pc", 0)),
                source=self.name,
            )
            result[symbol] = quote

        return result

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取ETF行情

        Args:
            symbols: ETF代码列表

        Returns:
            ETF行情字典
        """
        # Finnhub不直接支持ETF，通过股票代码获取
        return self.get_quote(symbols) if symbols else {}

    def get_all_stocks(self) -> List[Quote]:
        """获取全部股票列表

        Finnhub免费版不支持，返回空列表。
        建议使用 Akshare 或 Baostock 获取A股列表。
        """
        print("Warning: get_all_stocks not supported in Finnhub free tier")
        return []

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        """获取K线数据

        Args:
            symbol: 股票代码
            period: K线周期 (1h, 1d, 1w, 1M)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            K线数据列表
        """
        fmt_symbol = self._format_symbol(symbol)

        # 周期映射到Finnhub格式
        resolution_map = {
            "1h": "60",
            "1d": "D",
            "daily": "D",
            "1w": "W",
            "weekly": "W",
            "1M": "M",
            "monthly": "M",
        }
        resolution = resolution_map.get(period, "D")

        # 日期转换
        if end_date is None:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")

        if start_date is None:
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")

        unix_start = int(start_date.timestamp())
        unix_end = int(end_date.timestamp())

        data = self._get(
            "/stock/candle",
            {"symbol": fmt_symbol, "resolution": resolution, "from": unix_start, "to": unix_end},
        )

        if not data or data.get("s") != "ok":
            return []

        closes = data.get("c", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        volumes = data.get("v", [])
        timestamps = data.get("t", [])

        result = []
        for i in range(len(closes)):
            dt = datetime.fromtimestamp(timestamps[i])
            date_str = dt.strftime("%Y-%m-%d")

            kline = KLine(
                symbol=symbol,
                date=date_str,
                open=_safe_float(opens[i]) if i < len(opens) else 0,
                high=_safe_float(highs[i]) if i < len(highs) else 0,
                low=_safe_float(lows[i]) if i < len(lows) else 0,
                close=_safe_float(closes[i]),
                volume=_safe_int(volumes[i]) if i < len(volumes) else 0,
                amount=0.0,
                source=self.name,
            )
            result.append(kline)

        return result

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        """获取分钟数据

        Args:
            symbol: 股票代码
            date: 日期 (YYYY-MM-DD)

        Returns:
            分钟数据列表
        """
        # Finnhub免费版支持1分钟数据
        fmt_symbol = self._format_symbol(symbol)

        if date is None:
            end_date = int(datetime.now().timestamp())
            start_date = end_date - 86400  # 最近24小时
        else:
            dt = datetime.strptime(date, "%Y-%m-%d")
            start_date = int(dt.timestamp())
            end_date = start_date + 86400

        data = self._get(
            "/stock/candle",
            {"symbol": fmt_symbol, "resolution": "1", "from": start_date, "to": end_date},
        )

        if not data or data.get("s") != "ok":
            return []

        closes = data.get("c", [])
        volumes = data.get("v", [])
        timestamps = data.get("t", [])

        result = []
        for i in range(len(closes)):
            dt = datetime.fromtimestamp(timestamps[i])
            time_str = dt.strftime("%H:%M:%S")

            minute = MinuteData(
                symbol=symbol,
                time=time_str,
                price=_safe_float(closes[i]),
                volume=_safe_int(volumes[i]) if i < len(volumes) else 0,
                amount=0.0,
                source=self.name,
            )
            result.append(minute)

        return result

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本面信息

        Args:
            symbol: 股票代码

        Returns:
            StockInfo: 基本面数据
        """
        fmt_symbol = self._format_symbol(symbol)

        # 获取公司信息
        info = self._get("/stock/profile2", {"symbol": fmt_symbol})
        if not info:
            return None

        # 获取财务指标
        metrics = self._get("/stock/metric", {"symbol": fmt_symbol, "metric": "all"})

        market_cap = _safe_float(info.get("shareOutstanding", 0)) * _safe_float(
            info.get("country", 0)
        )

        metric_data = metrics.get("metric", {}) if metrics else {}

        return StockInfo(
            symbol=symbol,
            name=info.get("name", symbol),
            price=_safe_float(info.get("close", 0)),
            change_pct=0.0,
            pe=_safe_float(metric_data.get("peExclExtraTTM", 0)),
            pe_ttm=_safe_float(metric_data.get("peInclExtraTTM", 0)),
            pb=_safe_float(metric_data.get("pbAnnual", 0)),
            market_cap=market_cap,
            eps=_safe_float(metric_data.get("epsExclExtraItemsAnnual", 0)),
            beta=_safe_float(metric_data.get("beta", 0)),
            source=self.name,
        )
