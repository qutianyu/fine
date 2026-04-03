"""Company Data command - 获取公司数据"""

import csv
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def cmd_cd(args) -> int:
    """获取公司数据"""
    from fine.providers import MarketData

    symbols = args.symbols.replace(",", " ").split()
    provider_name = args.provider or "baostock"
    api_key = args.api_key
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")

    try:
        provider_kwargs = {"api_token": api_key} if api_key else {}
        market_data = MarketData(provider=provider_name, **provider_kwargs)

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
