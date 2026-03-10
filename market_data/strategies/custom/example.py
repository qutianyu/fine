"""
自定义策略示例

在此文件中添加你的自定义策略。

示例:

from fine.market_data.strategy import Strategy, SignalType, StockSignal, StrategyResult
from fine.market_data.providers import MarketData
from typing import List

class MyStrategy(Strategy):
    name = "my_strategy"
    description = "我的自定义策略"
    
    def __init__(self, param1: int = 10):
        self.param1 = param1
    
    def generate_signals(
        self, symbols: List[str], market_data: MarketData, **kwargs
    ) -> StrategyResult:
        signals = []
        # 实现你的策略逻辑
        ...
        return StrategyResult(signals=signals, selected=[s.symbol for s in signals])
"""
