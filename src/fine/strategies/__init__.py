import importlib.util
import os
import sys

from fine.strategies.strategy import Strategy


__all__ = [
    "Strategy",
    "get_strategy",
    "load_strategy_from_file",
]


def load_strategy_from_file(
    file_path: str,
    **kwargs,
) -> Strategy:
    """从文件路径加载策略

    Args:
        file_path: 策略文件路径 (如 /tmp/XXXX.py)

    Returns:
        Strategy 实例

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件中未找到策略类

    Example:
        # /tmp/my_strategy.py
        from fine.strategies.strategy import Strategy

        class MyStrategy(Strategy):
            name = "my_strategy"
            symbols = ["sh600519"]
            cash = 1000000

            def compute(self, symbol, data, indicators):
                # 策略逻辑
                pass

        # 使用:
        strategy = load_strategy_from_file("/tmp/my_strategy.py")
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Strategy file not found: {file_path}")

    module_name = os.path.splitext(os.path.basename(file_path))[0]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Failed to load module from: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    strategy_class = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, Strategy)
            and attr is not Strategy
        ):
            strategy_class = attr
            break

    if strategy_class is None:
        raise ValueError(
            f"No Strategy subclass found in {file_path}. "
            "Please define a class that inherits from Strategy."
        )

    return strategy_class()


def get_strategy(
    source: str,
    **kwargs,
) -> Strategy:
    """加载策略

    支持文件路径: 如 /tmp/XXXX.py, ./my_strategy.py

    Args:
        source: 策略文件路径

    Returns:
        Strategy 实例
    """
    source = source.strip()

    if os.path.isfile(source):
        return load_strategy_from_file(source, **kwargs)

    if source.endswith(".py"):
        return load_strategy_from_file(source, **kwargs)

    raise ValueError(
        f"Strategy file not found: {source}. "
        "Please provide a valid file path."
    )
