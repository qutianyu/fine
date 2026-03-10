"""
策略模块 - 自定义策略目录

结构:
    strategies/
    ├── __init__.py          # 主入口，自动发现策略
    ├── builtins/            # 内置策略
    │   └── __init__.py
    └── custom/              # 自定义策略 (用户编写)
        └── __init__.py

使用方式:
    from fine.market.strategies import MyCustomStrategy

    # 或从 custom 目录导入
    from fine.market.strategies.custom import my_strategy
"""

import importlib
from pathlib import Path
from typing import List, Type

# 从主模块导入所有基础类和内置策略
# 保持向后兼容
from ...strategy import (
    SignalType,
    StockSignal,
    StrategyResult,
    Condition,
    PriceCondition,
    VolumeCondition,
    IndicatorCondition,
    CompositeCondition,
    ChangeCondition,
    TurnoverCondition,
    CrossCondition,
    CustomCondition,
    Strategy,
    IndicatorFilterStrategy,
    MovingAverageStrategy,
    MACDStrategy,
    RSIStrategy,
    BrickChartStrategy,
    SimpleFunctionStrategy,
    StrategyBuilder,
    EnsembleStrategy,
    StrategyRegistry,
    create_strategy,
    scan_stocks,
    _CustomSignalStrategy,
)

BUILTIN_STRATEGIES = [
    IndicatorFilterStrategy,
    MovingAverageStrategy,
    MACDStrategy,
    RSIStrategy,
    BrickChartStrategy,
    SimpleFunctionStrategy,
    EnsembleStrategy,
]


def load_custom_strategies() -> List[Type[Strategy]]:
    """自动加载 custom 目录下的自定义策略

    扫描 strategies/custom/ 目录下的所有 .py 文件，
    自动导入并注册继承自 Strategy 的类。

    Returns:
        List[Type[Strategy]]: 自定义策略类列表
    """
    custom_strategies = []
    custom_dir = Path(__file__).parent / "custom"

    if not custom_dir.exists():
        return custom_strategies

    # 扫描 custom 目录下的所有 .py 文件
    for py_file in custom_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        module_name = f"market.strategies.custom.{py_file.stem}"

        try:
            module = importlib.import_module(module_name)

            # 查找所有 Strategy 子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Strategy)
                    and attr is not Strategy
                    and attr is not SimpleFunctionStrategy
                    and attr is not _CustomSignalStrategy
                    and attr is not EnsembleStrategy
                ):
                    # 检查是否有 name 属性（策略标识）
                    if hasattr(attr, "name") and attr.name:
                        custom_strategies.append(attr)
                        # 自动注册到 StrategyRegistry
                        StrategyRegistry.register(attr)

        except ImportError as e:
            # 忽略导入错误（可能是缺少依赖）
            print(f"Warning: Failed to import {module_name}: {e}")

    return custom_strategies


# 自动加载自定义策略
_custom_loaded = False


def get_custom_strategies(force_reload: bool = False) -> List[Type[Strategy]]:
    """获取已加载的自定义策略

    Args:
        force_reload: 是否强制重新加载

    Returns:
        List[Type[Strategy]]: 自定义策略类列表
    """
    global _custom_loaded

    if not _custom_loaded or force_reload:
        load_custom_strategies()
        _custom_loaded = True

    # 返回所有已注册的非内置策略
    all_registered = StrategyRegistry.list_strategies()
    builtin_names = {s.name for s in BUILTIN_STRATEGIES}

    custom = []
    for name in all_registered:
        if name not in builtin_names:
            strategy_cls = StrategyRegistry._strategies.get(name)
            if strategy_cls:
                custom.append(strategy_cls)

    return custom


# ============ 便捷函数 ============


def list_all_strategies() -> List[str]:
    """列出所有可用策略"""
    return StrategyRegistry.list_strategies()


def list_builtin_strategies() -> List[str]:
    result = []
    for s in BUILTIN_STRATEGIES:
        try:
            inst = s()
            name = inst.name
            name = str(name) if name else s.__name__
        except Exception:
            name = s.__name__
        result.append(name)
    return result


def list_custom_strategies() -> List[str]:
    """列出自定义策略"""
    custom = get_custom_strategies()
    return [s.name for s in custom]


# ============ 示例自定义策略 ============


# 如果 custom 目录为空，创建一个示例文件
def _ensure_custom_example():
    """确保 custom 目录有示例文件"""
    custom_dir = Path(__file__).parent / "custom"
    example_file = custom_dir / "example.py"

    if example_file.exists():
        return

    example_content = '''"""
自定义策略示例

在此文件中添加你的自定义策略。

示例:

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
        # 实现你的策略逻辑
        ...
        return StrategyResult(signals=signals, selected=[s.symbol for s in signals])
"""
'''
    example_file.write_text(example_content)


# 初始化时确保示例存在
_ensure_custom_example()


__all__ = [
    # 基础类
    "SignalType",
    "StockSignal",
    "StrategyResult",
    "Condition",
    "PriceCondition",
    "VolumeCondition",
    "IndicatorCondition",
    "CompositeCondition",
    "ChangeCondition",
    "TurnoverCondition",
    "CrossCondition",
    "CustomCondition",
    "Strategy",
    # 内置策略
    "IndicatorFilterStrategy",
    "MovingAverageStrategy",
    "MACDStrategy",
    "RSIStrategy",
    "BrickChartStrategy",
    "SimpleFunctionStrategy",
    "StrategyBuilder",
    "EnsembleStrategy",
    "BUILTIN_STRATEGIES",
    # 注册中心
    "StrategyRegistry",
    "create_strategy",
    "scan_stocks",
    # 工具函数
    "load_custom_strategies",
    "get_custom_strategies",
    "list_all_strategies",
    "list_builtin_strategies",
    "list_custom_strategies",
]
