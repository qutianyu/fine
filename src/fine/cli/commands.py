"""
CLI Commands - Command implementations for Fine CLI
"""

import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from ..backtest import (
    Backtest,
    BacktestConfig,
    StaticStockPool,
)
from ..providers import MarketData, create_provider
from ..strategies import get_strategy
from .i18n import get_i18n


def get_timestamp() -> str:
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")


def get_work_dir(config: Dict[str, Any]) -> str:
    work_dir = config.get("work_dir", "./output")
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def ensure_timestamp(config: Dict[str, Any]) -> str:
    if "_timestamp" not in config:
        config["_timestamp"] = get_timestamp()
    return config["_timestamp"]


def save_result(config: Dict[str, Any], result: Any) -> str:
    work_dir = get_work_dir(config)
    ts = ensure_timestamp(config)
    result_path = os.path.join(work_dir, f"result_{ts}.md")
    chart_path = os.path.join(work_dir, f"chart_{ts}.png")
    i18n = get_i18n(config)

    generate_chart(result, chart_path)

    with open(result_path, "w", encoding="utf-8") as f:
        f.write(f"# {i18n['backtest_result']}\n\n")
        f.write(f"**{i18n['timestamp']}**: {ts}\n\n")

        f.write(f"## {i18n['capital']}\n\n")
        f.write(f"- {i18n['initial']}: {result.initial_capital:,.2f}\n")
        f.write(f"- {i18n['final']}: {result.final_capital:,.2f}\n")

        if hasattr(result, "metrics") and result.metrics:
            m = result.metrics
            f.write(f"\n## {i18n['performance']}\n\n")
            f.write(f"- {i18n['total_return']}: {m.total_return:.2f}%\n")
            f.write(f"- {i18n['annualized_return']}: {m.annualized_return:.2f}%\n")
            f.write(f"- {i18n['sharpe_ratio']}: {m.sharpe_ratio:.2f}\n")
            f.write(f"- {i18n['max_drawdown']}: {m.max_drawdown:.2f}%\n")
            f.write(f"- {i18n['win_rate']}: {m.win_rate:.2f}%\n")
            f.write(f"- {i18n['total_trades']}: {m.total_trades}\n")

        f.write(f"\n## {i18n['chart']}\n\n")
        f.write(f"![Equity Curve](chart_{ts}.png)\n")

        if hasattr(result, "trades") and result.trades:
            f.write(f"\n## {i18n['trades']} (first 20)\n\n")
            f.write(
                f"| {i18n['date']} | {i18n['symbol']} | {i18n['action']} | {i18n['price']} | {i18n['shares']} |\n"
            )
            f.write(f"|------|--------|--------|-------|--------|\n")
            for trade in result.trades[:20]:
                f.write(
                    f"| {trade.date} | {trade.symbol} | {trade.action} | {trade.price:.2f} | {trade.shares} |\n"
                )
            if len(result.trades) > 20:
                f.write(f"\n*... and {len(result.trades) - 20} {i18n['more_trades']}*\n")

    return result_path


def save_result_markdown(path: str, config: Dict[str, Any], result: Any) -> None:
    """保存回测结果为 markdown 文件"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# 回测结果\n\n")

        f.write(f"**策略**: {config.get('strategy_name', 'strategy')}\n\n")
        f.write(f"**股票池**: {', '.join(config.get('symbols', []))}\n\n")
        f.write(f"**时间范围**: {config.get('start_date', '')} ~ {config.get('end_date', '')}\n\n")

        f.write(f"## 资金\n\n")
        f.write(f"- 初始资金: {result.initial_capital:,.2f}\n")
        f.write(f"- 最终资金: {result.final_capital:,.2f}\n")

        if hasattr(result, "metrics") and result.metrics:
            m = result.metrics
            f.write(f"\n## 绩效指标\n\n")
            f.write(f"- 总收益率: {m.total_return:.2f}%\n")
            f.write(f"- 年化收益率: {m.annualized_return:.2f}%\n")
            f.write(f"- 夏普比率: {m.sharpe_ratio:.2f}\n")
            f.write(f"- 最大回撤: {m.max_drawdown:.2f}%\n")
            f.write(f"- 胜率: {m.win_rate:.2f}%\n")
            f.write(f"- 总交易次数: {m.total_trades}\n")

        if hasattr(result, "trades") and result.trades:
            f.write(f"\n## 交易记录 (前20条)\n\n")
            f.write(f"| 日期 | 股票代码 | 操作 | 价格 | 数量 |\n")
            f.write(f"|------|---------|------|------|------|\n")
            for trade in result.trades[:20]:
                f.write(
                    f"| {trade.date} | {trade.symbol} | {trade.action} | {trade.price:.2f} | {trade.shares} |\n"
                )
            if len(result.trades) > 20:
                f.write(f"\n*... 共 {len(result.trades)} 条交易记录*\n")


def generate_chart(result: Any, chart_path: str) -> None:
    try:
        matplotlib.use("Agg")

        if not hasattr(result, "equity_curve") or not result.equity_curve:
            return

        df = pd.DataFrame(result.equity_curve)
        if df.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(pd.to_datetime(df["date"]), df["value"], label="Equity", linewidth=2)

        if hasattr(result, "benchmark_curve") and result.benchmark_curve:
            bench_df = pd.DataFrame(result.benchmark_curve)
            if not bench_df.empty:
                ax.plot(
                    pd.to_datetime(bench_df["date"]),
                    bench_df["value"],
                    label="Benchmark",
                    linewidth=1.5,
                    alpha=0.7,
                )

        ax.set_xlabel("Date")
        ax.set_ylabel("Value")
        ax.set_title("Equity Curve")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(chart_path, dpi=150)
        plt.close()
    except Exception as e:
        print(f"Warning: Failed to generate chart: {e}")


def fetch_benchmarks(
    market_data: MarketData,
    symbols: list,
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> Dict[str, list]:
    """获取基准数据用于对比"""
    result = {}
    for symbol in symbols:
        klines = market_data.get_kline(symbol, start_date=start_date, end_date=end_date)
        if not klines:
            continue
        initial_price = klines[0].close
        curve = []
        for kl in klines:
            value = (kl.close / initial_price) * initial_capital
            curve.append({"date": kl.date, "value": value})
        result[symbol] = curve
    return result


class FileMarketData:
    """从 CSV 文件加载数据的 MarketData 包装类"""

    def __init__(self, df: pd.DataFrame):
        self._df = df
        self._data_by_symbol: Dict[str, List] = {}
        for symbol, group in df.groupby("symbol"):
            self._data_by_symbol[symbol] = group.to_dict("records")

    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List:
        """获取 K 线数据"""
        from fine.providers import KLine

        if symbol not in self._data_by_symbol:
            return []

        klines = []
        for record in self._data_by_symbol[symbol]:
            date = record.get("date")
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
            klines.append(
                KLine(
                    symbol=symbol,
                    date=date,
                    open=record.get("open", 0),
                    close=record.get("close", 0),
                    high=record.get("high", 0),
                    low=record.get("low", 0),
                    volume=record.get("volume", 0),
                )
            )

        return sorted(klines, key=lambda x: x.date)


def run_backtest(config: Dict[str, Any]) -> Any:
    """根据配置运行回测

    配置格式:
    {
        "data_file": "/path/to/data.csv",  # 可选，从文件加载数据
        "provider": "akshare",              # 可选，数据提供商
        "symbols": ["sh600519", "sh000001"],
        "strategy": "macd",
        "cash": 1000000,
        "fee_rate": {
            "commission_rate": 0.0003,
            "min_commission": 5.0,
            "stamp_duty": 0.001,
            "transfer_fee": 0.00002
        },
        "period": "1d",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "store_type": "csv",
        "work_dir": "."
    }
    """
    data_file = config.get("data_file")

    if data_file:
        df = pd.read_csv(data_file)
        market_data = FileMarketData(df)
    else:
        provider_name = config.get("provider", "akshare")
        provider = create_provider(provider_name)
        market_data = MarketData(provider=provider_name)

    symbols_config = config.get("symbols", [])
    if isinstance(symbols_config, list):
        stock_pool = StaticStockPool(symbols_config)
    else:
        raise ValueError("Invalid symbols config")

    backtest_config = BacktestConfig()
    backtest_config.initial_capital = config.get("cash", 1000000)

    fee_rate = config.get("fee_rate", {})
    backtest_config.commission_rate = fee_rate.get("commission_rate", 0.0003)
    backtest_config.slippage = fee_rate.get("slippage", 0.0)
    backtest_config.stamp_duty = fee_rate.get("stamp_duty", 0.001)
    backtest_config.transfer_fee = fee_rate.get("transfer_fee", 0.00002)
    backtest_config.min_commission = fee_rate.get("min_commission", 5.0)

    backtest_config.stock_pool = stock_pool
    backtest_config.start_date = config.get("start_date", "2024-01-01")
    backtest_config.end_date = config.get("end_date", "2024-12-31")
    backtest_config.period = config.get("period", "1d")

    strategy_source = config.get("strategy", "")
    strategy = get_strategy(strategy_source)
    backtest_config.strategy = strategy

    backtest = Backtest()
    result = backtest.run(config=backtest_config, market_data=market_data)

    benchmarks = config.get("benchmark", [])
    if benchmarks:
        result.benchmark_data = fetch_benchmarks(
            market_data,
            benchmarks,
            backtest_config.start_date,
            backtest_config.end_date,
            result.initial_capital,
        )

    result_dir = config.get("result")
    if result_dir:
        os.makedirs(result_dir, exist_ok=True)
        strategy_name = config.get("strategy_name", "strategy")
        if "." in strategy_name:
            strategy_name = os.path.splitext(os.path.basename(strategy_name))[0]
        md_path = os.path.join(result_dir, f"{strategy_name}.md")
        save_result_markdown(md_path, config, result)
        print(f"\nResult saved to: {md_path}")

    if config.get("work_dir"):
        result_path = save_result(config, result)
        print(f"\nResult saved to: {result_path}")

    return result
