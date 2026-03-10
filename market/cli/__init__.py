#!/usr/bin/env python3
"""
Fine CLI - Command Line Interface for Fine

Usage:
    python -m fine run --config config.json
    python -m fine backtest --config config.json
    python -m fine indicator --config config.json
    python -m fine data --config config.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from market import __version__


class FineCLI:
    """Fine CLI 主类"""

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令行解析器"""
        parser = argparse.ArgumentParser(
            prog="fine",
            description="Fine - Python Market Data and Trading Backtesting Library",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
    # Run with config file
    fine run --config config.json

    # Backtest
    fine backtest --config backtest.json

    # Calculate indicators
    fine indicator --config indicator.json

    # Fetch data
    fine data --config data.json

    # Show version
    fine --version
            """
        )

        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {__version__}",
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # run 命令
        self._add_run_parser(subparsers)

        # backtest 命令
        self._add_backtest_parser(subparsers)

        # indicator 命令
        self._add_indicator_parser(subparsers)

        # data 命令
        self._add_data_parser(subparsers)

        return parser

    def _add_run_parser(self, subparsers) -> None:
        """添加 run 子命令"""
        parser = subparsers.add_parser("run", help="Run fine with config file")
        parser.add_argument(
            "--config", "-c", required=True, help="Path to config JSON file"
        )
        parser.add_argument(
            "--output", "-o", help="Output file path (default: stdout)"
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Verbose output"
        )

    def _add_backtest_parser(self, subparsers) -> None:
        """添加 backtest 子命令"""
        parser = subparsers.add_parser("backtest", help="Run backtest")
        parser.add_argument(
            "--config", "-c", required=True, help="Path to config JSON file"
        )
        parser.add_argument(
            "--output", "-o", help="Output result to file"
        )
        parser.add_argument(
            "--export-trades", help="Export trades to CSV file"
        )

    def _add_indicator_parser(self, subparsers) -> None:
        """添加 indicator 子命令"""
        parser = subparsers.add_parser("indicator", help="Calculate indicators")
        parser.add_argument(
            "--config", "-c", required=True, help="Path to config JSON file"
        )
        parser.add_argument(
            "--output", "-o", help="Output result to file (CSV/JSON)"
        )
        parser.add_argument(
            "--symbol", "-s", help="Single symbol to calculate"
        )

    def _add_data_parser(self, subparsers) -> None:
        """添加 data 子命令"""
        parser = subparsers.add_parser("data", help="Fetch market data")
        parser.add_argument(
            "--config", "-c", required=True, help="Path to config JSON file"
        )
        parser.add_argument(
            "--output", "-o", help="Output directory"
        )
        parser.add_argument(
            "--cache", action="store_true", default=True, help="Use cache"
        )

    def run(self, args: Optional[list] = None) -> int:
        """运行 CLI"""
        parsed = self.parser.parse_args(args)

        if not parsed.command:
            self.parser.print_help()
            return 1

        # 加载配置文件
        config = self._load_config(getattr(parsed, "config", None))

        # 执行命令
        try:
            return self._execute_command(parsed.command, parsed, config)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if getattr(parsed, "verbose", False):
                import traceback
                traceback.print_exc()
            return 1

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        if not config_path:
            return {}

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _execute_command(
        self, command: str, args: argparse.Namespace, config: Dict[str, Any]
    ) -> int:
        """执行命令"""
        if command == "run":
            return self._cmd_run(args, config)
        elif command == "backtest":
            return self._cmd_backtest(args, config)
        elif command == "indicator":
            return self._cmd_indicator(args, config)
        elif command == "data":
            return self._cmd_data(args, config)
        else:
            print(f"Unknown command: {command}")
            return 1

    def _cmd_run(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """执行 run 命令"""
        from .commands import run_task

        result = run_task(config)

        # 输出结果
        output = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Result saved to: {args.output}")
        else:
            print(output)

        return 0

    def _cmd_backtest(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """执行 backtest 命令"""
        from .commands import run_backtest

        result = run_backtest(config)

        # 打印结果
        self._print_backtest_result(result)

        # 导出交易记录
        if args.export_trades and hasattr(result, "export_trades_to_csv"):
            result.export_trades_to_csv(args.export_trades)
            print(f"Trades exported to: {args.export_trades}")

        # 保存结果
        if args.output:
            output_data = {
                "metrics": result.metrics.to_dict() if hasattr(result, "metrics") else {},
                "initial_capital": result.initial_capital,
                "final_capital": result.final_capital,
            }
            Path(args.output).write_text(
                json.dumps(output_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Result saved to: {args.output}")

        return 0

    def _cmd_indicator(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """执行 indicator 命令"""
        from .commands import calculate_indicators

        result = calculate_indicators(config)

        # 输出结果
        if args.output:
            import pandas as pd

            if isinstance(result, pd.DataFrame):
                result.to_csv(args.output, index=False)
            else:
                Path(args.output).write_text(
                    json.dumps(result, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            print(f"Result saved to: {args.output}")
        else:
            import pandas as pd

            if isinstance(result, pd.DataFrame):
                print(result.to_string())
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))

        return 0

    def _cmd_data(self, args: argparse.Namespace, config: Dict[str, Any]) -> int:
        """执行 data 命令"""
        from .commands import fetch_data

        result = fetch_data(config)

        # 保存数据
        output_dir = Path(args.output) if args.output else Path("data")
        output_dir.mkdir(exist_ok=True)

        import pandas as pd

        if isinstance(result, dict):
            for symbol, df in result.items():
                filepath = output_dir / f"{symbol}.csv"
                if isinstance(df, pd.DataFrame):
                    df.to_csv(filepath, index=False)
                print(f"Saved: {filepath}")
        elif isinstance(result, pd.DataFrame):
            filepath = output_dir / "data.csv"
            result.to_csv(filepath, index=False)
            print(f"Saved: {filepath}")

        return 0

    def _print_backtest_result(self, result) -> None:
        """打印回测结果"""
        print("\n" + "=" * 50)
        print("Backtest Result")
        print("=" * 50)
        print(f"Initial Capital: {result.initial_capital:,.2f}")
        print(f"Final Capital: {result.final_capital:,.2f}")

        if hasattr(result, "metrics"):
            m = result.metrics
            print(f"\nPerformance Metrics:")
            print(f"  Total Return: {m.total_return:.2f}%")
            print(f"  Annualized Return: {m.annualized_return:.2f}%")
            print(f"  Sharpe Ratio: {m.sharpe_ratio:.2f}")
            print(f"  Max Drawdown: {m.max_drawdown:.2f}%")
            print(f"  Win Rate: {m.win_rate:.2f}%")
            print(f"  Total Trades: {m.total_trades}")


def main() -> int:
    """主入口"""
    cli = FineCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
