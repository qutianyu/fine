#!/usr/bin/env python3
"""
Fine CLI - Command Line Interface for Fine

Usage:
    fine backtest --cash 1000000 --data /path/to/data.csv --strategy /path/to/strategy.py
    fine data --symbols sh600519,sh600001 --date 2024-01-01,2025-01-01 --period 1d --result /tmp
    fine calculate --indicator kdj,macd --data /tmp/20260314191231.csv --result /tmp
"""

import argparse
import csv
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from fine.config import get_config
from fine.indicators import TechnicalIndicators
from fine.providers import MarketData
from fine.strategies import get_strategy

from .commands import run_backtest

__version__ = "0.1.0"


def _load_config() -> Dict[str, Any]:
    """加载配置文件"""
    try:
        config = get_config()
        return {"provider": config.provider, "period": config.period}
    except Exception:
        return {"provider": "akshare", "period": "1d"}


INDICATOR_COLUMNS = {
    "kdj": ["k", "d", "j"],
    "macd": ["macd", "signal", "hist"],
    "rsi": ["rsi"],
    "wr": ["wr"],
    "cci": ["cci"],
    "atr": ["atr"],
    "obv": ["obv"],
    "mfi": ["mfi"],
    "cmf": ["cmf"],
    "vr": ["vr"],
}


def _cmd_data(args) -> int:
    """获取股票数据"""
    symbols = args.symbols.replace(",", " ").split()
    date_range = args.date.split(",")
    if len(date_range) != 2:
        print("Error: --date must be in format: start,end", file=sys.stderr)
        return 1

    start_date = date_range[0].strip()
    end_date = date_range[1].strip()
    period = args.period or "1d"
    provider_name = args.provider or "akshare"
    force = args.force
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")

    try:
        market_data = MarketData(provider=provider_name)

        all_klines: List[Dict[str, Any]] = []

        for symbol in symbols:
            klines = market_data.get_kline(
                symbol, period=period, start_date=start_date, end_date=end_date, force=force
            )
            for kl in klines:
                all_klines.append(
                    {
                        "symbol": symbol,
                        "date": kl.date,
                        "open": kl.open,
                        "close": kl.close,
                        "high": kl.high,
                        "low": kl.low,
                        "volume": kl.volume,
                    }
                )

        if not all_klines:
            print("No data fetched", file=sys.stderr)
            return 1

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        result_file = result_dir / f"{timestamp}.csv"
        result_dir.mkdir(parents=True, exist_ok=True)

        fieldnames = ["symbol", "date", "open", "close", "high", "low", "volume"]
        with open(result_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_klines:
                writer.writerow(row)

        print(str(result_file))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


def _cmd_calculate(args) -> int:
    """计算技术指标"""
    indicator_names = [x.strip().lower() for x in args.indicator.split(",")]
    data_file = Path(args.data)
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")

    if not data_file.exists():
        print(f"Error: Data file not found: {data_file}", file=sys.stderr)
        return 1

    try:
        df = pd.read_csv(data_file)

        required_cols = {"symbol", "date", "open", "close", "high", "low", "volume"}
        if not required_cols.issubset(set(df.columns)):
            print(f"Error: CSV must contain columns: {required_cols}", file=sys.stderr)
            return 1

        ti = TechnicalIndicators()
        result_dfs = []

        for symbol, group in df.groupby("symbol"):
            group = group.sort_values("date").reset_index(drop=True)

            close = group["close"].values
            high = group["high"].values
            low = group["low"].values
            volume = group["volume"].values

            ohlcv = {
                "close": close,
                "high": high,
                "low": low,
                "volume": volume,
                "open": group["open"].values,
            }

            for ind_name in indicator_names:
                try:
                    result = ti.compute(ind_name, ohlcv)
                    if result is None:
                        continue

                    cols = INDICATOR_COLUMNS.get(ind_name, [])
                    if isinstance(result, dict):
                        for col in cols:
                            if col in result:
                                group[col] = result[col]
                            elif hasattr(result, col):
                                group[col] = getattr(result, col)
                    elif hasattr(result, "values"):
                        if len(cols) == 1:
                            group[cols[0]] = result.values
                        else:
                            for i, col in enumerate(cols):
                                if i < result.shape[1]:
                                    group[col] = result[:, i]
                except Exception as e:
                    print(
                        f"Warning: Failed to compute {ind_name} for {symbol}: {e}",
                        file=sys.stderr,
                    )

            result_dfs.append(group)

        if not result_dfs:
            print("Error: No data after calculation", file=sys.stderr)
            return 1

        result_df = pd.concat(result_dfs, ignore_index=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        result_file = result_dir / f"{timestamp}.csv"
        result_dir.mkdir(parents=True, exist_ok=True)

        result_df.to_csv(result_file, index=False)

        print(str(result_file))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


def _cmd_backtest(args) -> int:
    """运行回测"""
    data_file = Path(args.data)

    if not data_file.exists():
        print(f"Error: Data file not found: {data_file}", file=sys.stderr)
        return 1

    try:
        df = pd.read_csv(data_file)

        required_cols = {"symbol", "date", "open", "close", "high", "low", "volume"}
        if not required_cols.issubset(set(df.columns)):
            print(f"Error: CSV must contain columns: {required_cols}", file=sys.stderr)
            return 1

        symbols = df["symbol"].unique().tolist()
        start_date = df["date"].min()
        end_date = df["date"].max()

    except Exception as e:
        print(f"Error reading data file: {e}", file=sys.stderr)
        return 1

    try:
        strategy = get_strategy(args.strategy)
    except Exception as e:
        print(f"Error loading strategy: {e}")
        return 1

    strategy_name = getattr(strategy, "name", "strategy")

    config = {
        "cash": args.cash if args.cash is not None else getattr(strategy, "cash", 1000000),
        "data_file": str(data_file),
        "symbols": symbols,
        "strategy": args.strategy,
        "strategy_name": strategy_name,
        "period": args.period or getattr(strategy, "period", "1d"),
        "start_date": start_date,
        "end_date": end_date,
        "fee_rate": {
            "commission_rate": (
                args.commission
                if args.commission is not None
                else getattr(strategy, "commission_rate", 0.0003)
            ),
            "min_commission": (
                args.min_commission
                if args.min_commission is not None
                else getattr(strategy, "min_commission", 5.0)
            ),
            "stamp_duty": (
                args.stamp_duty
                if args.stamp_duty is not None
                else getattr(strategy, "stamp_duty", 0.001)
            ),
            "transfer_fee": (
                args.transfer_fee
                if args.transfer_fee is not None
                else getattr(strategy, "transfer_fee", 0.00002)
            ),
        },
        "result": args.result,
    }

    try:
        result = run_backtest(config)

        output = []
        output.append("\n" + "=" * 50)
        output.append("Backtest Result")
        output.append("=" * 50)
        output.append(f"Initial Capital: {result.initial_capital:,.2f}")
        output.append(f"Final Capital: {result.final_capital:,.2f}")

        if hasattr(result, "metrics"):
            m = result.metrics
            output.append(f"\nPerformance Metrics:")
            output.append(f"  Total Return: {m.total_return:.2f}%")
            output.append(f"  Annualized Return: {m.annualized_return:.2f}%")
            output.append(f"  Sharpe Ratio: {m.sharpe_ratio:.2f}")
            output.append(f"  Max Drawdown: {m.max_drawdown:.2f}%")
            output.append(f"  Win Rate: {m.win_rate:.2f}%")
            output.append(f"  Total Trades: {m.total_trades}")

        output_str = "\n".join(output)

        print(output_str)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fine", description="Fine - Python Market Data and Trading Backtesting Library"
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    data_parser = subparsers.add_parser("data", help="Fetch stock data")
    data_parser.add_argument(
        "--symbols", type=str, required=True, help="Stock symbols (comma or space separated)"
    )
    data_parser.add_argument("--date", type=str, required=True, help="Date range (start,end)")
    data_parser.add_argument(
        "--period",
        type=str,
        default="1d",
        choices=["1h", "1d", "1w", "1M"],
        help="Period (default: 1d)",
    )
    data_parser.add_argument(
        "--provider",
        type=str,
        default="akshare",
        choices=["akshare", "baostock", "yfinance", "baidu"],
        help="Data provider (default: akshare)",
    )
    data_parser.add_argument(
        "--force",
        action="store_true",
        help="Force fetch from data source, ignore cache",
    )
    data_parser.add_argument("--result", type=str, help="Output directory")

    backtest_parser = subparsers.add_parser("backtest", help="Run backtest")
    backtest_parser.add_argument("--cash", type=float, help="Initial cash")
    backtest_parser.add_argument("--data", type=str, required=True, help="Data CSV file")
    backtest_parser.add_argument("--strategy", type=str, required=True, help="Strategy file path")
    backtest_parser.add_argument("--period", type=str, help="Period")
    backtest_parser.add_argument("--commission", type=float, help="Commission rate")
    backtest_parser.add_argument("--min-commission", type=float, help="Minimum commission")
    backtest_parser.add_argument("--stamp-duty", type=float, help="Stamp duty rate")
    backtest_parser.add_argument("--transfer-fee", type=float, help="Transfer fee rate")
    backtest_parser.add_argument("--result", type=str, help="Output directory")

    calc_parser = subparsers.add_parser("calculate", help="Calculate technical indicators")
    calc_parser.add_argument(
        "--indicator", type=str, required=True, help="Indicators (comma separated)"
    )
    calc_parser.add_argument("--data", type=str, required=True, help="Input CSV file")
    calc_parser.add_argument("--result", type=str, help="Output directory")

    args = parser.parse_args()

    if args.command == "data":
        return _cmd_data(args)
    elif args.command == "backtest":
        return _cmd_backtest(args)
    elif args.command == "calculate":
        return _cmd_calculate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
