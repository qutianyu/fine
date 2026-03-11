"""
Fine Client - Client for connecting to Fine server

Usage:
    fine client ip:port              # Interactive mode
    fine client ip:port --config config.json  # One-shot mode
"""

import json
import shlex
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


class FineClient:
    """Client for Fine server"""

    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"
        self.task_id: Optional[str] = None

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make HTTP request"""
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            # Check if response is JSON
            try:
                return response.json()
            except:
                return response
        except requests.exceptions.ConnectionError:
            print(f"Error: Cannot connect to server at {self.base_url}")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"Error: {e}")
            sys.exit(1)

    def health_check(self) -> bool:
        """Check server health"""
        try:
            result = self._request("GET", "/health")
            return result.get("status") == "healthy"
        except Exception:
            return False

    def get_config(self) -> Dict[str, Any]:
        """Get server config"""
        return self._request("GET", "/config")

    def submit_backtest(self, config_path: str) -> Optional[str]:
        """Submit a backtest task"""
        path = Path(config_path)
        if not path.exists():
            print(f"Error: Config file not found: {config_path}")
            return None

        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        data = {"type": "backtest", "config": config}
        result = self._request("POST", "/tasks", json=data)

        self.task_id = result.get("task_id")
        return self.task_id if self.task_id else None

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        return self._request("GET", f"/tasks/{task_id}")

    def get_result(self, task_id: str, output_path: Optional[str] = None, wait: bool = True) -> None:
        """Get task result"""
        if wait:
            print(f"Waiting for task {task_id} to complete...")

            while True:
                status = self.get_task_status(task_id)
                task_status = status.get("status")

                if task_status == "completed":
                    break
                elif task_status == "failed":
                    print(f"Task failed: {status.get('error')}")
                    return
                else:
                    print(f"Status: {task_status}... ", end="\r")
                    time.sleep(2)

            print()

        status = self.get_task_status(task_id)
        
        if output_path:
            result = self._request("GET", f"/tasks/{task_id}/result")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.text if hasattr(result, "text") else str(result))
            print(f"Result saved to: {output_path}")
        else:
            result_data = status.get("result", {})
            print("\n" + "=" * 50)
            print("Backtest Result")
            print("=" * 50)
            print(f"Initial Capital: {result_data.get('initial_capital', 0):,.2f}")
            print(f"Final Capital: {result_data.get('final_capital', 0):,.2f}")

            metrics = result_data.get("metrics", {})
            print(f"\nPerformance Metrics:")
            print(f"  Total Return: {metrics.get('total_return', 0):.2f}%")
            print(f"  Annualized Return: {metrics.get('annualized_return', 0):.2f}%")
            print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
            print(f"  Win Rate: {metrics.get('win_rate', 0):.2f}%")
            print(f"  Total Trades: {metrics.get('total_trades', 0)}")

            if status.get("result_file"):
                print(f"\nResult file: {status['result_file']}")

    def list_tasks(self) -> None:
        """List all tasks"""
        result = self._request("GET", "/tasks")
        tasks = result.get("tasks", [])

        if not tasks:
            print("No tasks found")
            return

        print("\nTasks:")
        print("-" * 70)
        for task in tasks:
            print(f"ID: {task['id']} | Type: {task['type']} | Status: {task['status']} | Created: {task['created_at']}")


def run_interactive(client: FineClient) -> None:
    """Run interactive mode like redis-cli"""
    print(f"Fine Client - Connected to {client.base_url}")
    print("Type 'help' for commands.\n")

    while True:
        try:
            cmd = input("fine> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not cmd:
            continue

        parts = shlex.split(cmd)
        if not parts:
            continue

        command = parts[0].lower()
        args = parts[1:]

        if command in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        elif command == "help":
            print("""
Commands:
  backtest <config.json>  Submit a backtest task
  result <task_id>        Get task result
  result <task_id> -o <file>  Save result to file
  list                    List all tasks
  status <task_id>       Get task status
  config                 Show server config
  health                 Check server health
  help                   Show this help
  quit                   Exit
""")

        elif command == "backtest":
            if not args:
                print("Usage: backtest <config.json>")
                continue
            config_path = args[0]
            task_id = client.submit_backtest(config_path)
            if task_id:
                print(f"Task submitted: {task_id}")

        elif command == "result":
            if not args:
                print("Usage: result <task_id> [-o output.md]")
                continue
            
            task_id = args[0]
            output_path = None
            if "-o" in args:
                idx = args.index("-o")
                if idx + 1 < len(args):
                    output_path = args[idx + 1]
            
            client.get_result(task_id, output_path)

        elif command == "status":
            if not args:
                print("Usage: status <task_id>")
                continue
            task_id = args[0]
            status = client.get_task_status(task_id)
            print(json.dumps(status, indent=2))

        elif command == "list":
            client.list_tasks()

        elif command == "config":
            cfg = client.get_config()
            print(json.dumps(cfg, indent=2))

        elif command == "health":
            if client.health_check():
                print("Server is healthy")
            else:
                print("Server is not responding")

        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands.")


def run_client(args: List[str]) -> int:
    """Run client commands"""
    import argparse

    parser = argparse.ArgumentParser(prog="fine client", description="Fine Client")
    parser.add_argument("server", nargs="?", help="Server address (e.g., localhost:8080)")
    parser.add_argument("--backtest", metavar="CONFIG", help="Submit backtest task with config file")
    parser.add_argument("--result", metavar="TASK_ID", help="Get task result")
    parser.add_argument("--output", "-o", metavar="FILE", help="Output file for result")
    parser.add_argument("--list", action="store_true", help="List all tasks")
    parser.add_argument("--health", action="store_true", help="Check server health")
    parser.add_argument("--wait", action="store_true", default=True, help="Wait for task to complete (default: True)")
    parser.add_argument("--no-wait", action="store_false", dest="wait", help="Don't wait for task to complete")

    parsed = parser.parse_args(args)

    # If no server specified at all, show help
    if not parsed.server:
        print("Error: Server address required")
        print("Usage: fine client <host:port>")
        print("   or: fine client <host:port> --health")
        print("   or: fine client <host:port> --backtest client_config.json")
        return 1

    # Parse server address
    if ":" in parsed.server:
        host, port = parsed.server.rsplit(":", 1)
        port = int(port)
    else:
        host = parsed.server
        port = 8080

    client = FineClient(host, port)

    # Check if any command flag was provided
    has_command = parsed.health or parsed.list or parsed.backtest or parsed.result

    # If no command flag, enter interactive mode
    if not has_command:
        run_interactive(client)
        return 0

    # If any command specified, run it and exit
    if parsed.health:
        if client.health_check():
            print("Server is healthy")
            return 0
        else:
            print("Server is not responding")
            return 1

    if parsed.list:
        client.list_tasks()
        return 0

    if parsed.backtest:
        task_id = client.submit_backtest(parsed.backtest)
        if task_id:
            print(f"Task submitted: {task_id}")
            if parsed.wait:
                client.get_result(str(task_id), parsed.output, wait=True)
        return 0

    if parsed.result:
        client.get_result(parsed.result, parsed.output, wait=parsed.wait)
        return 0

    # No command - enter interactive mode
    run_interactive(client)
    return 0
