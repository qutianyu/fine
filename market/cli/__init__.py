#!/usr/bin/env python3
"""
Fine CLI - Command Line Interface for Fine

Usage:
    fine --config client_config.json        # Run backtest directly
    fine start --port 8080          # Start Fine server
    fine client ip:port --submit client_config.json  # Submit task to server
    fine client ip:port --result task_id      # Get task result
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from market import __version__


class FineCLI:
    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="fine",
            description="Fine - Python Market Data and Trading Backtesting Library",
        )

        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {__version__}",
        )

        subparsers = parser.add_subparsers(dest="command", help="Commands")

        # backtest command (default)
        backtest_parser = subparsers.add_parser("backtest", help="Run backtest locally")
        backtest_parser.add_argument(
            "--config", required=True, help="Path to config JSON file"
        )

        # start command
        start_parser = subparsers.add_parser("start", help="Start Fine server")
        start_parser.add_argument(
            "--config", default="server_config.json", help="Server config file (default: server_config.json)"
        )
        start_parser.add_argument(
            "--port", "-p", type=int, help="Server port (override config)"
        )
        start_parser.add_argument(
            "--host", help="Server host (override config)"
        )
        start_parser.add_argument(
            "--work-dir", help="Work directory for tasks (override config)"
        )

        # client command
        client_parser = subparsers.add_parser("client", help="Connect to Fine server")
        client_parser.add_argument("server", nargs="?", help="Server address (e.g., localhost:8080)")
        client_parser.add_argument("--backtest", metavar="CONFIG", help="Submit backtest task with config file")
        client_parser.add_argument("--result", metavar="TASK_ID", help="Get task result")
        client_parser.add_argument("--output", "-o", metavar="FILE", help="Output file for result")
        client_parser.add_argument("--list", action="store_true", help="List all tasks")
        client_parser.add_argument("--health", action="store_true", help="Check server health")
        client_parser.add_argument(
            "--wait", action="store_true", help="Wait for task to complete"
        )

        # Default: run backtest with --config
        parser.add_argument(
            "--config", help="Path to config JSON file (for direct backtest)"
        )

        return parser

    def run(self, args: Optional[list] = None) -> int:
        parsed = self.parser.parse_args(args)

        # No command, use --config for direct backtest
        if parsed.command is None:
            if parsed.config:
                return self._cmd_backtest_file(parsed.config)
            else:
                self.parser.print_help()
                return 1

        if parsed.command == "backtest":
            return self._cmd_backtest_file(parsed.config)

        elif parsed.command == "start":
            return self._cmd_start(parsed)

        elif parsed.command == "client":
            return self._cmd_client(parsed)

        return 0

    def _cmd_backtest_file(self, config_path: str) -> int:
        config = self._load_config(config_path)
        try:
            return self._cmd_backtest(config)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _cmd_backtest(self, config: Dict[str, Any]) -> int:
        from .commands import run_backtest

        result = run_backtest(config)

        self._print_backtest_result(result)

        return 0

    def _cmd_start(self, args) -> int:
        """Start Fine server"""
        from market.server import start_server

        start_server(
            config_path=args.config,
            port=args.port,
            host=args.host,
            work_dir=args.work_dir,
        )
        return 0

    def _cmd_client(self, args) -> int:
        """Run client commands"""
        from market.client import FineClient, run_interactive

        # Parse server address
        if ":" in args.server:
            host, port = args.server.rsplit(":", 1)
            port = int(port)
        else:
            host = args.server
            port = 8080

        client = FineClient(host, port)

        # Check if any command flag was provided
        has_command = args.health or args.list or args.backtest or args.result

        # If no command flag, enter interactive mode
        if not has_command:
            run_interactive(client)
            return 0

        if args.health:
            if client.health_check():
                print("Server is healthy")
                return 0
            else:
                print("Server is not responding")
                return 1

        if args.list:
            client.list_tasks()
            return 0

        if args.backtest:
            task_id = client.submit_backtest(args.backtest)
            print(f"Task submitted: {task_id}")
            print(f"Use 'fine client {args.server} --result {task_id}' to get result")
            return 0

        if args.result:
            client.get_result(args.result, args.output)
            return 0

        return 0

    def _print_backtest_result(self, result) -> None:
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
    cli = FineCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
