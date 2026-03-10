"""
CLI Commands - Command implementations for Fine CLI
"""

from typing import Any, Dict, Union
import pandas as pd

from ..providers import create_provider
from ..backtest import (
    Backtest,
    BacktestConfig,
    StaticStockPool,
    FileStockPool,
)
from ..strategy import create_strategy
from ..indicators import TechnicalIndicators
from ..cache import get_cache


def run_task(config: Dict[str, Any]) -> Any:
    """运行通用任务

    根据配置执行相应任务
    """
    task_type = config.get("task_type", "backtest")

    if task_type == "backtest":
        return run_backtest(config)
    elif task_type == "indicator":
        return calculate_indicators(config)
    elif task_type == "data":
        return fetch_data(config)
    else:
        raise ValueError(f"Unknown task type: {task_type}")


def run_backtest(config: Dict[str, Any]) -> Any:
    """运行回测

    配置示例:
    {
        "provider": "akshare",
        "symbols": ["sh600519", "sh000001"],
        "strategy": "macd",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "initial_capital": 1000000,
        "commission_rate": 0.0003
    }
    """
    # 获取数据提供者
    provider_name = config.get("provider", "akshare")
    provider = create_provider(provider_name)

    # 获取股票池 (使用 symbols 字段)
    symbols_config = config.get("symbols", config.get("stock_pool", []))
    if isinstance(symbols_config, list):
        stock_pool = StaticStockPool(symbols_config)
    elif isinstance(symbols_config, str):
        stock_pool = FileStockPool(symbols_config)
    else:
        raise ValueError("Invalid symbols config")

    # 创建策略
    strategy_name = config.get("strategy", "macd")
    strategy_params = config.get("strategy_params", {})
    strategy = create_strategy(strategy_name, **strategy_params)

    # 回测配置
    backtest_config = BacktestConfig(
        initial_capital=config.get("initial_capital", 1000000),
        commission_rate=config.get("commission_rate", 0.0003),
        slippage=config.get("slippage", 0.0),
    )

    # 运行回测
    backtest = Backtest(
        config=backtest_config,
        stock_pool=stock_pool,
        strategy=strategy,
        data_provider=provider,
    )

    result = backtest.run(
        start_date=config.get("start_date", "2023-01-01"),
        end_date=config.get("end_date", "2024-01-01"),
    )

    return result


def calculate_indicators(config: Dict[str, Any]) -> Union[pd.DataFrame, Dict]:
    """计算指标

    配置示例:
    {
        "symbols": ["sh600519"],
        "indicators": ["MA", "MACD", "RSI"],
        "period": "daily",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01"
    }
    """
    # 获取数据
    provider_name = config.get("provider", "akshare")
    provider = create_provider(provider_name)

    symbols = config.get("symbols", [])
    indicators = config.get("indicators", ["MA"])
    start_date = config.get("start_date")
    end_date = config.get("end_date")

    # 创建指标计算器
    ti = TechnicalIndicators()

    results = {}

    for symbol in symbols:
        # 获取K线数据
        klines = provider.get_kline(
            symbol,
            period=config.get("period", "daily"),
            start_date=start_date,
            end_date=end_date,
        )

        if not klines:
            continue

        # 转换为DataFrame
        df = pd.DataFrame([k.to_dict() for k in klines])

        # 计算指标
        symbol_results = {"symbol": symbol, "date": df["date"].tolist()}

        for indicator in indicators:
            try:
                result = ti.compute(indicator, df)
                if hasattr(result, "__len__") and not isinstance(result, dict):
                    symbol_results[indicator] = result.tolist()
                elif isinstance(result, dict):
                    for k, v in result.items():
                        symbol_results[f"{indicator}_{k}"] = (
                            v.tolist() if hasattr(v, "tolist") else v
                        )
            except Exception as e:
                print(f"Error computing {indicator} for {symbol}: {e}")

        results[symbol] = symbol_results

    # 如果只有一个symbol，返回DataFrame
    if len(symbols) == 1:
        return pd.DataFrame(results[symbols[0]])

    return results


def fetch_data(config: Dict[str, Any]) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """获取市场数据

    配置示例:
    {
        "provider": "akshare",
        "data_type": "kline",  # kline, quote, stock_info
        "symbols": ["sh600519", "sh000001"],
        "period": "daily",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "cache": true
    }
    """
    provider_name = config.get("provider", "akshare")
    provider = create_provider(provider_name)

    data_type = config.get("data_type", "kline")
    symbols = config.get("symbols", [])
    use_cache = config.get("cache", True)

    # 缓存
    cache = None
    if use_cache:
        cache = get_cache("csv", cache_dir=config.get("cache_dir", ".fine_cache"))

    results = {}

    for symbol in symbols:
        # 检查缓存
        if cache and data_type == "kline":
            cached = cache.get_kline(symbol, config.get("period", "daily"))
            if cached is not None:
                results[symbol] = pd.DataFrame([k if isinstance(k, dict) else k.to_dict() for k in cached])
                continue

        # 获取数据
        if data_type == "kline":
            data = provider.get_kline(
                symbol,
                period=config.get("period", "daily"),
                start_date=config.get("start_date"),
                end_date=config.get("end_date"),
            )
            df = pd.DataFrame([k.to_dict() for k in data])

            # 缓存
            if cache:
                cache.set_kline(symbol, data, period=config.get("period", "daily"), ttl=config.get("cache_ttl", 3600))

        elif data_type == "quote":
            data = provider.get_quote(symbol)
            df = pd.DataFrame([q.to_dict() for q in data.values()])

        elif data_type == "stock_info":
            data = provider.get_stock_info(symbol)
            df = pd.DataFrame([data.to_dict()]) if data else pd.DataFrame()

        else:
            raise ValueError(f"Unknown data_type: {data_type}")

        results[symbol] = df

    # 如果只有一个symbol，返回DataFrame
    if len(symbols) == 1:
        return results[symbols[0]]

    return results
