#!/usr/bin/env python3
"""
Fine CLI - Command Line Interface for Fine

Usage:
    fine backtest --cash 1000000 --data /path/to/data.csv --strategy /path/to/strategy.py
    fine pd --symbols sh600519,sh600001 --start-time 2024-01-01 00:00 --end-time 2025-01-01 00:00 --period 1d --result /tmp
    fine cd --symbols sh600519,sh600000
    fine calculate --type indicator --data /tmp/data.csv --result /tmp
    fine news --result /tmp
"""

import argparse
import sys

__version__ = "0.3.2"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fine",
        description="Fine - 市场价格数据与交易回测 CLI 工具",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="命令列表")

    # pd command
    data_parser = subparsers.add_parser("pd", help="获取价格数据 (K线)")
    data_parser.add_argument(
        "--symbols",
        type=str,
        required=True,
        help="股票代码 (逗号或空格分隔)",
    )
    data_parser.add_argument(
        "--start-time", type=str, required=True, help="开始日期 (yyyy-MM-dd HH:mm)"
    )
    data_parser.add_argument(
        "--end-time", type=str, required=True, help="结束日期 (yyyy-MM-dd HH:mm)"
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
        choices=["akshare", "baostock", "yfinance", "baidu", "finnhub", "tushare", "eastmoney"],
        help="数据源 (默认: akshare)",
    )
    data_parser.add_argument("--api-key", type=str, help="API Key (finnhub/tushare 必填)")
    data_parser.add_argument("--result", type=str, help="输出目录")

    # backtest command
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
    backtest_parser.add_argument(
        "--lang",
        type=str,
        default="zh",
        choices=["zh", "en"],
        help="输出语言 (默认: zh)",
    )

    # calculate command
    calc_parser = subparsers.add_parser("calculate", help="计算技术指标、收益率或风险指标")
    calc_parser.add_argument(
        "--type",
        type=str,
        default="indicator",
        choices=["indicator", "returns", "rolling", "risk", "all"],
        help="计算类型 (默认: indicator)",
    )
    calc_parser.add_argument(
        "--indicator",
        type=str,
        help="技术指标 (逗号分隔, 仅在 type=indicator 时使用, 默认: ma,ema,macd,kdj,rsi,boll)",
    )
    calc_parser.add_argument("--data", type=str, required=True, help="输入CSV文件")
    calc_parser.add_argument("--result", type=str, help="输出目录")
    calc_parser.add_argument(
        "--window",
        type=int,
        default=20,
        help="滚动窗口大小 (仅在 type=rolling 时使用, 默认: 20)",
    )
    calc_parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.0,
        help="无风险利率年化 (仅在 type=risk 或 type=all 时使用, 默认: 0.0)",
    )

    # news command
    news_parser = subparsers.add_parser("news", help="获取新闻数据")
    news_parser.add_argument(
        "--provider",
        type=str,
        default="akshare",
        choices=["akshare", "xueqiu", "yicai", "sina", "wallstreetcn", "cctv", "economic"],
        help="新闻源 (默认: akshare)",
    )
    news_parser.add_argument(
        "--start-time",
        type=str,
        help="开始日期 (yyyy-MM-dd HH:mm)",
    )
    news_parser.add_argument(
        "--end-time",
        type=str,
        help="结束日期 (yyyy-MM-dd HH:mm)",
    )
    news_parser.add_argument("--result", type=str, help="输出目录 (默认: 当前目录)")
    news_parser.add_argument(
        "--keywords",
        type=str,
        help="关键词过滤 (空格分隔，如: 银行 钢铁)",
    )

    # cd command
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
        choices=["akshare", "baostock", "yfinance", "baidu", "eastmoney", "tushare"],
        help="数据源 (默认: akshare)",
    )
    cd_parser.add_argument("--api-key", type=str, help="API Key (tushare 必填)")
    cd_parser.add_argument("--result", type=str, help="输出目录")

    args = parser.parse_args()

    # Import and dispatch to command handlers
    if args.command == "pd":
        from .commands.data import cmd_data
        return cmd_data(args)
    elif args.command == "backtest":
        from pathlib import Path
        import pandas as pd
        from .backtest_cmd import run_backtest

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
            from fine.strategies import get_strategy
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
            "lang": args.lang,
        }

        return run_backtest(config)
    elif args.command == "calculate":
        from .commands.calculate import cmd_calculate
        return cmd_calculate(args)
    elif args.command == "news":
        from .commands.news import cmd_news
        return cmd_news(args)
    elif args.command == "cd":
        from .commands.cd import cmd_cd
        return cmd_cd(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
