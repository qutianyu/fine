"""
Market Data Provider Framework
支持多种数据源: 腾讯API、新浪API、Akshare等
"""

import requests
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class Quote:
    """实时行情数据"""

    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    amount: float
    open: float
    high: float
    low: float
    prev_close: float
    source: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KLine:
    """K线数据"""

    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    source: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MinuteData:
    """分时数据"""

    symbol: str
    time: str
    price: float
    volume: int
    amount: float
    source: str

    def to_dict(self) -> Dict:
        return asdict(self)


class DataProvider(ABC):
    """数据源抽象基类"""

    name: str = ""

    @abstractmethod
    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        """获取实时行情"""
        pass

    @abstractmethod
    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取指数行情"""
        pass

    @abstractmethod
    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取ETF行情"""
        pass

    @abstractmethod
    def get_all_stocks(self) -> List[Quote]:
        """获取全部股票列表"""
        pass

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
            period: K线周期 (daily/weekly/monthly)
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
        """
        return []

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        """获取分时数据

        Args:
            symbol: 股票代码
            date: 日期 YYYY-MM-DD，默认昨天
        """
        return []


class TencentProvider(DataProvider):
    """腾讯API数据源"""

    name = "tencent"
    BASE_URL = "https://qt.gtimg.cn/q="

    INDEX_CODES = [
        "sh000001",
        "sh000300",
        "sh000016",
        "sh000905",
        "sh000688",
        "sz399001",
        "sz399006",
        "sz399005",
    ]

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        if symbol.startswith(("sh", "sz")):
            return symbol
        if symbol.startswith("6"):
            return f"sh{symbol}"
        if symbol.startswith(("0", "3")):
            return f"sz{symbol}"
        return symbol

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        if isinstance(symbols, str):
            symbols = [symbols]

        codes = [TencentProvider._format_symbol(s) for s in symbols]
        url = self.BASE_URL + ",".join(codes)

        resp = requests.get(url, timeout=10)
        result = {}

        for line in resp.text.strip().split("\n"):
            if not line or "=" not in line:
                continue
            code, info = line.split("=")
            info = info.strip('";').split("~")
            symbol = code[-6:]

            if len(info) < 10:
                continue

            price = float(info[3])
            prev_close = float(info[4])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            result[symbol] = Quote(
                symbol=symbol,
                name=info[1],
                price=price,
                change=change,
                change_pct=change_pct,
                volume=int(float(info[6])),
                amount=float(info[37]) if len(info) > 37 else 0,
                open=float(info[5]),
                high=float(info[33]) if len(info) > 33 else price,
                low=float(info[34]) if len(info) > 34 else price,
                prev_close=prev_close,
                source=self.name,
            )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            symbols = self.INDEX_CODES
        if isinstance(symbols, str):
            symbols = [symbols]
        return self.get_quote(symbols)

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            return {}
        return self.get_quote(symbols)

    def get_all_stocks(self) -> List[Quote]:
        return []


class SinaProvider(DataProvider):
    """新浪API数据源"""

    name = "sina"
    BASE_URL = "https://hq.sinajs.cn/list="

    @staticmethod
    def _format_symbol(symbol: str) -> str:
        if symbol.startswith(("sh", "sz")):
            return symbol
        if symbol.startswith("6"):
            return f"sh{symbol}"
        if symbol.startswith(("0", "3")):
            return f"sz{symbol}"
        return symbol

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        if isinstance(symbols, str):
            symbols = [symbols]

        codes = [SinaProvider._format_symbol(s) for s in symbols]
        url = self.BASE_URL + ",".join(codes)

        headers = {"Referer": "https://finance.sina.com.cn"}
        resp = requests.get(url, headers=headers, timeout=10)
        result = {}

        for line in resp.text.strip().split("\n"):
            if "=" not in line:
                continue
            name, values = line.split("=")
            code = name[-8:-2]
            values = values.strip('";').split(",")

            if len(values) < 32:
                continue

            price = float(values[3])
            prev_close = float(values[2])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            result[code] = Quote(
                symbol=code,
                name=values[0],
                price=price,
                change=change,
                change_pct=change_pct,
                volume=int(float(values[8]) * 100),
                amount=float(values[9]),
                open=float(values[1]),
                high=float(values[4]),
                low=float(values[5]),
                prev_close=prev_close,
                source=self.name,
            )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        index_map = {
            "sh000001": "sh000001",
            "sz399001": "sz399001",
            "sz399006": "sz399006",
        }
        if symbols is None:
            symbols = list(index_map.keys())
        if isinstance(symbols, str):
            symbols = [symbols]
        return self.get_quote(symbols)

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        if symbols is None:
            return {}
        return self.get_quote(symbols)

    def get_all_stocks(self) -> List[Quote]:
        return []


class AkshareProvider(DataProvider):
    """Akshare数据源"""

    name = "akshare"

    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        import akshare as ak

        if isinstance(symbols, str):
            symbols = [symbols]

        df = ak.stock_zh_a_spot_em()
        df = df[df["代码"].isin(symbols)]

        result = {}
        for _, row in df.iterrows():
            symbol = row["代码"]
            result[symbol] = Quote(
                symbol=symbol,
                name=row["名称"],
                price=float(row["最新价"]) if row["最新价"] != "-" else 0,
                change=float(row["涨跌额"]) if row["涨跌额"] != "-" else 0,
                change_pct=float(row["涨跌幅"]) if row["涨跌幅"] != "-" else 0,
                volume=int(row["成交量"]) if row["成交量"] != "-" else 0,
                amount=float(row["成交额"]) if row["成交额"] != "-" else 0,
                open=float(row["今开"]) if row["今开"] != "-" else 0,
                high=float(row["最高"]) if row["最高"] != "-" else 0,
                low=float(row["最低"]) if row["最低"] != "-" else 0,
                prev_close=float(row["昨收"]) if row["昨收"] != "-" else 0,
                source=self.name,
            )
        return result

    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        import akshare as ak

        df = ak.stock_zh_index_spot_em()

        if symbols:
            df = df[df["代码"].isin(symbols)]
            result = {}
            for _, row in df.iterrows():
                symbol = row["代码"]
                result[symbol] = self._row_to_quote(row)
            return result

        return [self._row_to_quote(row) for _, row in df.iterrows()]

    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        import akshare as ak

        df = ak.fund_etf_spot_em()

        if symbols:
            if isinstance(symbols, str):
                symbols = [symbols]
            df = df[df["代码"].isin(symbols)]
            result = {}
            for _, row in df.iterrows():
                symbol = row["代码"]
                result[symbol] = self._row_to_quote(row)
            return result

        return [self._row_to_quote(row) for _, row in df.iterrows()]

    def get_all_stocks(self) -> List[Quote]:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
        return [self._row_to_quote(row) for _, row in df.iterrows()]

    @staticmethod
    def _row_to_quote(row) -> Quote:
        return Quote(
            symbol=row["代码"],
            name=row["名称"],
            price=float(row["最新价"]) if row["最新价"] != "-" else 0,
            change=float(row["涨跌额"]) if row["涨跌额"] != "-" else 0,
            change_pct=float(row["涨跌幅"]) if row["涨跌幅"] != "-" else 0,
            volume=int(row["成交量"]) if row["成交量"] != "-" else 0,
            amount=float(row["成交额"]) if row["成交额"] != "-" else 0,
            open=float(row["今开"]) if row["今开"] != "-" else 0,
            high=float(row["最高"]) if row["最高"] != "-" else 0,
            low=float(row["最低"]) if row["最低"] != "-" else 0,
            prev_close=float(row["昨收"]) if row["昨收"] != "-" else 0,
            source="akshare",
        )

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[KLine]:
        import akshare as ak

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        symbol = symbol.replace("sh", "").replace("sz", "")

        try:
            if period == "daily":
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
            elif period == "weekly":
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="weekly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
            elif period == "monthly":
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="monthly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
            else:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )

            result = []
            for _, row in df.iterrows():
                result.append(
                    KLine(
                        symbol=symbol,
                        date=str(row["日期"]),
                        open=float(row["开盘"]),
                        high=float(row["最高"]),
                        low=float(row["最低"]),
                        close=float(row["收盘"]),
                        volume=int(float(row["成交量"])),
                        amount=float(row["成交额"]),
                        source=self.name,
                    )
                )
            return result
        except Exception as e:
            print(f"Error fetching kline: {e}")
            return []

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        import akshare as ak

        symbol = symbol.replace("sh", "").replace("sz", "")

        try:
            df = ak.stock_zh_a_minute(
                symbol=f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}",
                period="5",
                adjust="",
            )

            result = []
            for _, row in df.iterrows():
                result.append(
                    MinuteData(
                        symbol=symbol,
                        time=str(row["day"]),
                        price=float(row["close"]),
                        volume=int(row["volume"]),
                        amount=float(row["amount"])
                        if "amount" in row and row["amount"]
                        else 0,
                        source=self.name,
                    )
                )
            return result
        except Exception as e:
            print(f"Error fetching minute data: {e}")
            return []


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


ProviderRegistry.register(TencentProvider)
ProviderRegistry.register(SinaProvider)
ProviderRegistry.register(AkshareProvider)


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
        from .indicators import compute_indicators

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

    @classmethod
    def list_providers(cls) -> List[str]:
        return ProviderRegistry.list_providers()


def create_provider(name: str) -> DataProvider:
    """创建数据源实例"""
    return ProviderRegistry.get(name)


__all__ = [
    "MarketData",
    "DataProvider",
    "Quote",
    "ProviderRegistry",
    "create_provider",
    "TencentProvider",
    "SinaProvider",
    "AkshareProvider",
]
