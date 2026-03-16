from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

KLINE_COLUMNS = [
    "symbol",  # 股票代码
    "name",  # 股票名称
    "period",  # 时间维度 (1d, 1h, etc.)
    "open",  # 开盘价
    "close",  # 最新价
    "high",  # 最高价
    "low",  # 最低价
    "volume",  # 成交量
]

STOCK_INFO_COLUMNS = [
    "symbol",  # 股票代码
    "name",  # 股票名称
    "price",  # 当前价格
    "change_pct",  # 涨跌幅
    "pe",  # 市盈率
    "pe_ttm",  # 市盈率TTM
    "pe_lyr",  # 市盈率LYR
    "pb",  # 市净率
    "market_cap",  # 总市值
    "float_market_cap",  # 流通市值
    "total_shares",  # 总股本
    "float_shares",  # 流通股本
    "turnover_rate",  # 换手率
    "volume_ratio",  # 量比
    "high_52w",  # 52周最高
    "low_52w",  # 52周最低
    "eps",  # 每股收益
    "bps",  # 每股净资产
    "roe",  # 净资产收益率
    "gross_margin",  # 毛利率
    "net_margin",  # 净利率
    "revenue",  # 营业收入
    "profit",  # 净利润
    "source",  # 数据源
]


class Store(ABC):
    """数据存储基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取存储的值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置存储的值"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除存储的值"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清除所有数据"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    def get_kline(self, symbol: str, period: str = "daily") -> Optional[Any]:
        """获取K线数据"""
        return self.get(f"kline:{symbol}:{period}")

    def set_kline(self, symbol: str, data: Any, period: str = "daily", ttl: int = 3600) -> None:
        """设置K线数据"""
        self.set(f"kline:{symbol}:{period}", data, ttl)

    @abstractmethod
    def query_klines(
        self,
        symbol: Optional[str] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询K线数据（带过滤条件）"""
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
        """保存单条K线记录"""
        pass

    @abstractmethod
    def save_klines(self, klines: List[Dict[str, Any]]) -> None:
        """保存多条K线记录"""
        pass

    @abstractmethod
    def save_stock_info(self, stock_info: Dict[str, Any]) -> None:
        """保存股票基本信息"""
        pass

    @abstractmethod
    def load_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """加载股票基本信息"""
        pass


class StoreRegistry:
    """存储类型注册中心（用于扩展）"""

    _store_types: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, store_class: type) -> None:
        """注册新的存储类型"""
        cls._store_types[name] = store_class

    @classmethod
    def get(cls, name: str) -> type:
        """根据名称获取存储类"""
        if name not in cls._store_types:
            raise ValueError(f"未知的存储类型: {name}。可用类型: {list(cls._store_types.keys())}")
        return cls._store_types[name]
