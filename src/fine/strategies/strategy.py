from abc import ABC, abstractmethod
from typing import List

from fine.period import Period
from fine.strategies.data import Data
from fine.strategies.indicators import Indicators
from fine.strategies.portfolio import Portfolio


class Strategy(ABC):
    """策略名称"""

    name: str = "base"
    """佣金费率 (默认万三 0.0003)"""
    commission_rate: float = 0.0003
    """最低佣金 (默认5元)"""
    min_commission: float = 5.0
    """印花税率 (默认千一 0.001，仅卖出收取)"""
    stamp_duty: float = 0.001
    """过户费率 (默认万分之0.2 = 0.00002)"""
    transfer_fee: float = 0.00002
    """基准信息"""
    benchmarks: List[str] = []
    """股票池"""
    symbols: List[str] = []
    """现金"""
    cash: float = 1000000.0
    """时间维度"""
    period: Period = Period.DAY_1
    """开始时间"""
    start_date: str = ""
    """结束时间"""
    end_date: str = ""

    @abstractmethod
    def compute(
        self,
        symbol: str,
        data: Data,
        indicators: Indicators,
        portfolio: Portfolio,
    ) -> None:
        pass
