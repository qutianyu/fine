"""
数据类型定义模块

定义市场数据的核心数据类型和Provider抽象基类。
支持Quote(实时行情)、KLine(K线)、MinuteData(分钟数据)、TickData(分时数据)四种数据类型。
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union

# Period mapping: standard -> provider format
PERIOD_MAP = {
    "1h": "60",
    "1d": "daily",
    "1w": "weekly",
    "1M": "monthly",
}


def normalize_period(period: str) -> str:
    """标准化周期字符串为标准格式"""
    mapping = {
        "60": "1h",
        "daily": "1d",
        "1d": "1d",
        "weekly": "1w",
        "1w": "1w",
        "monthly": "1M",
        "1m": "1M",
    }
    return mapping.get(period.lower(), period.lower())


def to_provider_period(period: str) -> str:
    """将周期转换为数据源特定格式"""
    return PERIOD_MAP.get(period, "daily")


@dataclass
class Quote:
    """实时行情数据

    包含股票的实时价格、涨跌幅、成交量等基本信息。

    Attributes:
        symbol: 股票代码 (如 sh600519)
        name: 股票名称
        price: 当前价格
        change: 涨跌额
        change_pct: 涨跌幅(%)
        volume: 成交量(手)
        amount: 成交额(元)
        open: 开盘价
        high: 最高价
        low: 最低价
        prev_close: 昨收价
        source: 数据源名称
        timestamp: 数据时间戳
    """

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
        """转换为字典格式"""
        return asdict(self)


@dataclass
class KLine:
    """K线数据(蜡烛图)

    包含K线的OHLCV数据，支持日/周/月周期。

    Attributes:
        symbol: 股票代码
        date: 交易日期
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        amount: 成交额
        source: 数据源名称
    """

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
        """转换为字典格式"""
        return asdict(self)


@dataclass
class MinuteData:
    """分钟数据

    包含分时成交的分钟级数据。

    Attributes:
        symbol: 股票代码
        time: 时间(HH:MM:SS格式)
        price: 成交价
        volume: 成交量
        amount: 成交额
        source: 数据源名称
    """

    symbol: str
    time: str
    price: float
    volume: int
    amount: float
    source: str

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return asdict(self)


@dataclass
class TickData:
    """逐笔数据

    包含每一笔成交的详细信息。

    Attributes:
        symbol: 股票代码
        time: 成交时间
        price: 成交价
        volume: 成交量
        change: 涨跌额
        amount: 成交额
        source: 数据源名称
    """

    symbol: str
    time: str
    price: float
    volume: int
    change: float
    amount: float
    source: str

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return asdict(self)


@dataclass
class StockInfo:
    """股票基本面数据

    包含股票的基本面信息，如市盈率、市值、净资产等。

    Attributes:
        symbol: 股票代码
        name: 股票名称
        price: 当前价格
        change_pct: 涨跌幅(%)
        pe: 市盈率(TTM)
        pe_ttm: 市盈率(TTM)
        pe_lyr: 市盈率(LYR)
        pb: 市净率
        market_cap: 总市值(元)
        float_market_cap: 流通市值(元)
        total_shares: 总股本(股)
        float_shares: 流通股本(股)
        turnover_rate: 换手率(%)
        volume_ratio: 量比
        high_52w: 52周最高
        low_52w: 52周最低
        eps: 每股收益
        bps: 每股净资产
        roe: 净资产收益率(%)
        gross_margin: 毛利率(%)
        net_margin: 净利率(%)
        revenue: 营业收入(元)
        profit: 净利润(元)
        source: 数据源名称
    """

    symbol: str
    name: str
    price: float = 0.0
    change_pct: float = 0.0
    pe: float = 0.0
    pe_ttm: float = 0.0
    pe_lyr: float = 0.0
    pb: float = 0.0
    market_cap: float = 0.0
    float_market_cap: float = 0.0
    total_shares: float = 0.0
    float_shares: float = 0.0
    turnover_rate: float = 0.0
    volume_ratio: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    eps: float = 0.0
    bps: float = 0.0
    roe: float = 0.0
    gross_margin: float = 0.0
    net_margin: float = 0.0
    revenue: float = 0.0
    profit: float = 0.0
    source: str = ""

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return asdict(self)


class DataProvider(ABC):
    """数据Provider抽象基类

    所有数据源需继承此类并实现抽象方法。
    支持获取实时行情、K线、分钟数据等。

    Attributes:
        name: 数据源名称
    """

    name: str = ""

    @abstractmethod
    def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Quote]:
        """获取实时行情

        Args:
            symbols: 股票代码，支持单只或列表

        Returns:
            Dict[symbol -> Quote]: 行情数据字典
        """
        pass

    @abstractmethod
    def get_index(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取指数行情

        Args:
            symbols: 指数代码，可选

        Returns:
            指数行情字典或列表
        """
        pass

    @abstractmethod
    def get_etf(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取ETF行情

        Args:
            symbols: ETF代码，可选

        Returns:
            ETF行情字典或列表
        """
        pass

    @abstractmethod
    def get_all_stocks(self) -> List[Quote]:
        """获取全部股票列表

        Returns:
            全部股票行情列表
        """
        pass

    def get_kline(
        self,
        symbol: str,
        period: str = "1d",
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
        return []

    def get_minute(self, symbol: str, date: Optional[str] = None) -> List[MinuteData]:
        """获取分钟数据

        Args:
            symbol: 股票代码
            date: 日期 (YYYY-MM-DD)，默认最新

        Returns:
            分钟数据列表
        """
        return []

    def get_hkstock(
        self, symbols: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Quote], List[Quote]]:
        """获取港股行情

        Args:
            symbols: 港股代码，可选

        Returns:
            港股行情字典或列表
        """
        return {}

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本面信息

        Args:
            symbol: 股票代码

        Returns:
            StockInfo: 基本面数据，未获取到则返回None
        """
        return None
