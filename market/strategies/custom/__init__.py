"""
自定义策略目录

在此目录下创建 .py 文件添加自定义策略。

文件结构示例:

    custom/
    ├── __init__.py       # 本文件
    ├── my_strategy.py    # 自定义策略文件
    └── another.py        # 另一个策略文件

示例 - 创建自定义策略 (my_strategy.py):

    from fine.market.strategy import Strategy, SignalType, StockSignal, StrategyResult
    from fine.market.providers import MarketData
    from typing import List

    class MyStrategy(Strategy):
        name = "my_strategy"
        description = "我的自定义策略"

        def __init__(self, param1: int = 10):
            self.param1 = param1

        def generate_signals(
            self, symbols: List[str], market: MarketData, **kwargs
        ) -> StrategyResult:
            signals = []
            # ... 实现策略逻辑
            return StrategyResult(
                signals=signals,
                selected=[s.symbol for s in signals]
            )

使用自定义策略:

    from fine.market.strategies import list_custom_strategies, StrategyRegistry

    # 查看已加载的自定义策略
    print(list_custom_strategies())

    # 或直接从模块导入
    from fine.market.strategies.custom.my_strategy import MyStrategy
"""

# 导入父模块以保持策略注册
from fine.market_data.strategies import (
    Strategy,
    SignalType,
    StockSignal,
    StrategyResult,
    StrategyRegistry,
)

__all__ = [
    "Strategy",
    "SignalType",
    "StockSignal",
    "StrategyResult",
    "StrategyRegistry",
]
