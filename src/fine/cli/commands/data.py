"""Data command - 获取股票价格数据"""

import csv
import os
import sys
import traceback
from pathlib import Path


def format_datetime(dt_str: str) -> str:
    """格式化日期时间为 YYYYMMDHHMM 格式"""
    dt_str = dt_str.replace("-", "").replace(":", "").replace(" ", "")
    if len(dt_str) == 8:
        dt_str += "0000"
    return dt_str


def cmd_data(args) -> int:
    """获取股票数据"""
    from fine.providers import MarketData

    symbols = args.symbols.replace(",", " ").split()
    start_date = args.start_time
    end_date = args.end_time
    period = args.period or "1d"
    provider_name = args.provider or "akshare"
    api_key = args.api_key
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")

    try:
        provider_kwargs = {"api_key": api_key} if api_key else {}
        market_data = MarketData(provider=provider_name, **provider_kwargs)

        result_dir.mkdir(parents=True, exist_ok=True)
        fieldnames = ["symbol", "date", "open", "close", "high", "low", "volume"]

        start_fmt = format_datetime(start_date)
        end_fmt = format_datetime(end_date)

        result_files = []

        for symbol in symbols:
            klines = market_data.get_kline(
                symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
            )

            if not klines:
                continue

            result_file = result_dir / f"{symbol}_{start_fmt}-{end_fmt}_{period}.csv"

            with open(result_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for kl in klines:
                    writer.writerow(
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

            result_files.append(str(result_file))

        if not result_files:
            print("No data fetched", file=sys.stderr)
            return 1

        print("\n".join(result_files))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
