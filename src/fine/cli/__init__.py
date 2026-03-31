#!/usr/bin/env python3
"""
Fine CLI - Command Line Interface for Fine

Usage:
    fine backtest --cash 1000000 --data /path/to/data.csv --strategy /path/to/strategy.py
    fine pd --symbols sh600519,sh600001 --start-date 2024-01-01 00:00 --end-date 2025-01-01 00:00 --period 1d --result /tmp
    fine cd --symbols sh600519,sh600000
    fine calculate --indicator kdj,macd --data /tmp/20260314191231.csv --result /tmp
    fine news --provider efinance --symbols sh600519 --result /tmp
    fine news --provider cctv --result /tmp
    fine news --provider economic --result /tmp
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
    start_date = args.start_date
    end_date = args.end_date
    period = args.period or "1d"
    provider_name = args.provider or "akshare"
    force = args.force
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")

    try:
        market_data = MarketData(provider=provider_name)

        all_klines: List[Dict[str, Any]] = []

        for symbol in symbols:
            klines = market_data.get_kline(
                symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                force=force,
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


def _cmd_news(args) -> int:
    """获取新闻数据"""
    news_provider = args.provider or "efinance"
    symbols = args.symbols.replace(",", " ").split() if args.symbols else []
    start_date = args.start_date or ""
    end_date = args.end_date or ""
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")

    try:
        market_data = MarketData(provider="akshare")

        result_dir.mkdir(parents=True, exist_ok=True)

        def format_date_for_filename(dt_str: str) -> str:
            if not dt_str:
                return "all"
            return dt_str.replace(":", "").replace(" ", "").replace("-", "")

        def write_news_to_markdown(news_list: List, symbol: str) -> Path:
            start_fmt = format_date_for_filename(start_date)
            end_fmt = format_date_for_filename(end_date)

            if symbol == "cctv" or symbol == "economic":
                filename = f"news-{symbol}-{start_fmt}-{end_fmt}.md"
            else:
                filename = f"news-{symbol}-{start_fmt}-{end_fmt}.md"

            result_file = result_dir / filename

            with open(result_file, "w", encoding="utf-8") as f:
                if symbol == "cctv":
                    f.write("# 央视新闻\n\n")
                elif symbol == "economic":
                    f.write("# 财经日历\n\n")
                else:
                    f.write(f"# 新闻 - {symbol}\n\n")

                for news in news_list:
                    f.write(f"## {news.publish_date}\n\n")
                    f.write(f"- **标题**: {news.title}\n")
                    f.write(f"- **来源**: {news.source}\n")
                    if news.url:
                        f.write(f"- **链接**: {news.url}\n")
                    if news.content:
                        f.write(f"- **内容**: {news.content}\n")
                    f.write("\n---\n\n")

            return result_file

        if news_provider == "efinance":
            if not symbols:
                print(
                    "Error: --symbols is required for efinance news provider",
                    file=sys.stderr,
                )
                return 1
            result_files = []
            for symbol in symbols:
                news_list = market_data.get_news(symbol=symbol, news_type="efinance")
                if news_list:
                    result_file = write_news_to_markdown(news_list, symbol)
                    result_files.append(str(result_file))
            if result_files:
                print("\n".join(result_files))
                return 0
            else:
                print("No news fetched", file=sys.stderr)
                return 1

        elif news_provider == "cctv":
            news_list = market_data.get_news(news_type="cctv")
            if news_list:
                result_file = write_news_to_markdown(news_list, "cctv")
                print(str(result_file))
                return 0
            else:
                print("No news fetched", file=sys.stderr)
                return 1

        elif news_provider == "economic":
            news_list = market_data.get_news(news_type="economic")
            if news_list:
                result_file = write_news_to_markdown(news_list, "economic")
                print(str(result_file))
                return 0
            else:
                print("No news fetched", file=sys.stderr)
                return 1

        else:
            print(f"Error: Unknown news provider: {news_provider}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


def _cmd_cd(args) -> int:
    """获取公司数据"""
    symbols = args.symbols.replace(",", " ").split()
    provider_name = args.provider or "akshare"
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")

    try:
        market_data = MarketData(provider=provider_name)

        all_data: List[Dict[str, Any]] = []

        for symbol in symbols:
            stock_info = market_data.get_stock_info(symbol)
            if stock_info:
                all_data.append(
                    {
                        "symbol": stock_info.symbol,
                        "name": stock_info.name,
                        "price": stock_info.price,
                        "change_pct": stock_info.change_pct,
                        "pe": stock_info.pe,
                        "pe_ttm": stock_info.pe_ttm,
                        "pb": stock_info.pb,
                        "market_cap": stock_info.market_cap,
                        "float_market_cap": stock_info.float_market_cap,
                        "total_shares": stock_info.total_shares,
                        "float_shares": stock_info.float_shares,
                        "turnover_rate": stock_info.turnover_rate,
                        "volume_ratio": stock_info.volume_ratio,
                        "high_52w": stock_info.high_52w,
                        "low_52w": stock_info.low_52w,
                        "eps": stock_info.eps,
                        "bps": stock_info.bps,
                        "roe": stock_info.roe,
                        "gross_margin": stock_info.gross_margin,
                        "net_margin": stock_info.net_margin,
                        "revenue": stock_info.revenue,
                        "profit": stock_info.profit,
                    }
                )

        if not all_data:
            print("No data fetched", file=sys.stderr)
            return 1

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        result_file = result_dir / f"company_{timestamp}.csv"
        result_dir.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "symbol",
            "name",
            "price",
            "change_pct",
            "pe",
            "pe_ttm",
            "pb",
            "market_cap",
            "float_market_cap",
            "total_shares",
            "float_shares",
            "turnover_rate",
            "volume_ratio",
            "high_52w",
            "low_52w",
            "eps",
            "bps",
            "roe",
            "gross_margin",
            "net_margin",
            "revenue",
            "profit",
        ]
        with open(result_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_data:
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
        prog="fine",
        description="Fine - Python 市场价格数据与交易回测库",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="命令列表")

    data_parser = subparsers.add_parser("pd", help="获取价格数据 (K线)")
    data_parser.add_argument(
        "--symbols",
        type=str,
        required=True,
        help="股票代码 (逗号或空格分隔)",
    )
    data_parser.add_argument(
        "--start-date", type=str, required=True, help="开始日期 (yyyy-MM-dd HH:mm)"
    )
    data_parser.add_argument(
        "--end-date", type=str, required=True, help="结束日期 (yyyy-MM-dd HH:mm)"
    )
    data_parser.add_argument(
        "--period",
        type=str,
        default="1d",
        choices=["1h", "1d", "1w", "1M"],
        help="周期 (默认: 1d)",
    )
    data_parser.add_argument(
        "--provider",
        type=str,
        default="akshare",
        choices=["akshare", "baostock", "yfinance", "baidu"],
        help="数据源 (默认: akshare)",
    )
    data_parser.add_argument(
        "--force",
        action="store_true",
        help="强制从数据源获取，忽略缓存",
    )
    data_parser.add_argument("--result", type=str, help="输出目录")

    backtest_parser = subparsers.add_parser("backtest", help="运行回测")
    backtest_parser.add_argument("--cash", type=float, help="初始资金")
    backtest_parser.add_argument("--data", type=str, required=True, help="数据CSV文件")
    backtest_parser.add_argument("--strategy", type=str, required=True, help="策略文件路径")
    backtest_parser.add_argument("--period", type=str, help="周期")
    backtest_parser.add_argument("--commission", type=float, help="佣金费率")
    backtest_parser.add_argument("--min-commission", type=float, help="最低佣金")
    backtest_parser.add_argument("--stamp-duty", type=float, help="印花税率")
    backtest_parser.add_argument("--transfer-fee", type=float, help="过户费率")
    backtest_parser.add_argument("--result", type=str, help="输出目录")

    calc_parser = subparsers.add_parser("calculate", help="计算技术指标")
    calc_parser.add_argument("--indicator", type=str, required=True, help="技术指标 (逗号分隔)")
    calc_parser.add_argument("--data", type=str, required=True, help="输入CSV文件")
    calc_parser.add_argument("--result", type=str, help="输出目录")

    news_parser = subparsers.add_parser("news", help="获取新闻数据")
    news_parser.add_argument(
        "--symbols",
        type=str,
        help="股票代码 (逗号或空格分隔)",
    )
    news_parser.add_argument(
        "--provider",
        type=str,
        default="efinance",
        choices=["efinance", "cctv", "economic"],
        help="新闻源 (efinance/cctv/economic，默认: efinance)",
    )
    news_parser.add_argument(
        "--start-date",
        type=str,
        help="开始日期 (yyyy-MM-dd HH:mm)",
    )
    news_parser.add_argument(
        "--end-date",
        type=str,
        help="结束日期 (yyyy-MM-dd HH:mm)",
    )
    news_parser.add_argument("--result", type=str, help="输出目录 (默认: 当前目录)")

    cd_parser = subparsers.add_parser("cd", help="获取公司数据 (市值、PE等)")
    cd_parser.add_argument(
        "--symbols",
        type=str,
        required=True,
        help="股票代码 (逗号或空格分隔)",
    )
    cd_parser.add_argument(
        "--provider",
        type=str,
        default="akshare",
        choices=["akshare", "baostock", "yfinance", "baidu"],
        help="数据源 (默认: akshare)",
    )
    cd_parser.add_argument("--result", type=str, help="输出目录")

    args = parser.parse_args()

    if args.command == "pd":
        return _cmd_data(args)
    elif args.command == "backtest":
        return _cmd_backtest(args)
    elif args.command == "calculate":
        return _cmd_calculate(args)
    elif args.command == "news":
        return _cmd_news(args)
    elif args.command == "cd":
        return _cmd_cd(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
