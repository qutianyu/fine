"""
CLI Commands - Command implementations for Fine CLI
"""

import os
from datetime import datetime
from typing import Any, Dict

import pandas as pd

from ..backtest import (
    Backtest,
    BacktestConfig,
    StaticStockPool,
    FileStockPool,
)
from ..cache import get_cache
from ..providers import create_provider, MarketData
from ..strategy import create_strategy

I18N = {
    "zh": {
        "backtest_result": "回测结果",
        "timestamp": "时间戳",
        "capital": "资金",
        "initial": "初始资金",
        "final": "最终资金",
        "performance": "性能指标",
        "total_return": "总收益率",
        "annualized_return": "年化收益率",
        "sharpe_ratio": "夏普比率",
        "max_drawdown": "最大回撤",
        "win_rate": "胜率",
        "total_trades": "交易次数",
        "chart": "图表",
        "trades": "交易记录",
        "date": "日期",
        "symbol": "股票",
        "action": "操作",
        "price": "价格",
        "shares": "数量",
        "more_trades": "更多交易记录",
    },
    "en": {
        "backtest_result": "Backtest Result",
        "timestamp": "Timestamp",
        "capital": "Capital",
        "initial": "Initial",
        "final": "Final",
        "performance": "Performance",
        "total_return": "Total Return",
        "annualized_return": "Annualized Return",
        "sharpe_ratio": "Sharpe Ratio",
        "max_drawdown": "Max Drawdown",
        "win_rate": "Win Rate",
        "total_trades": "Total Trades",
        "chart": "Chart",
        "trades": "Trades",
        "date": "Date",
        "symbol": "Symbol",
        "action": "Action",
        "price": "Price",
        "shares": "Shares",
        "more_trades": "more trades",
    },
}


def get_i18n(config: Dict[str, Any]) -> Dict[str, str]:
    lang = config.get("lang", "zh")
    return I18N.get(lang, I18N["zh"])


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


def save_cache(config: Dict[str, Any], provider) -> str:
    work_dir = get_work_dir(config)
    ts = ensure_timestamp(config)
    cache_path = os.path.join(work_dir, f"cache_{ts}.csv")
    return cache_path


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
        
        if hasattr(result, 'metrics') and result.metrics:
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
        
        if hasattr(result, 'trades') and result.trades:
            f.write(f"\n## {i18n['trades']} (first 20)\n\n")
            f.write(f"| {i18n['date']} | {i18n['symbol']} | {i18n['action']} | {i18n['price']} | {i18n['shares']} |\n")
            f.write(f"|------|--------|--------|-------|--------|\n")
            for trade in result.trades[:20]:
                f.write(f"| {trade.date} | {trade.symbol} | {trade.action} | {trade.price:.2f} | {trade.shares} |\n")
            if len(result.trades) > 20:
                f.write(f"\n*... and {len(result.trades) - 20} {i18n['more_trades']}*\n")
    
    return result_path


def generate_chart(result: Any, chart_path: str) -> None:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import pandas as pd
        
        if not hasattr(result, 'equity_curve') or not result.equity_curve:
            return
        
        df = pd.DataFrame(result.equity_curve)
        if df.empty:
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(pd.to_datetime(df['date']), df['value'], label='Equity', linewidth=2)
        
        if hasattr(result, 'benchmark_curve') and result.benchmark_curve:
            bench_df = pd.DataFrame(result.benchmark_curve)
            if not bench_df.empty:
                ax.plot(pd.to_datetime(bench_df['date']), bench_df['value'], 
                       label='Benchmark', linewidth=1.5, alpha=0.7)
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Value')
        ax.set_title('Equity Curve')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150)
        plt.close()
    except Exception as e:
        print(f"Warning: Failed to generate chart: {e}")


def fetch_benchmarks(market_data: MarketData, symbols: list, start_date: str, 
                     end_date: str, initial_capital: float) -> Dict[str, list]:
    """Fetch benchmark data for comparison"""
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


def run_backtest(config: Dict[str, Any]) -> Any:
    """运行回测

    配置示例 (模块化格式):
    {
        "provider": "akshare",
        "symbols": ["sh600519", "sh000001"],
        "strategy": {
            "name": "macd",
            "params": {"fast_period": 12, "slow_period": 26}
        },
        "cash": {
            "initial_capital": 1000000,
            "fee": {
                "commission_rate": 0.0003,
                "slippage": 0.001,
                "stamp_duty": 0.001
            }
        },
        "date": {
            "start": "2023-01-01",
            "end": "2024-01-01"
        },
        "backtest": {
            "position_size": 1.0,
            "max_positions": 10
        }
    }
    """
    provider_name = config.get("provider", "akshare")
    provider = create_provider(provider_name)
    market_data = MarketData(provider=provider_name)

    symbols_config = config.get("symbols", config.get("stock_pool", []))
    if isinstance(symbols_config, list):
        stock_pool = StaticStockPool(symbols_config)
    elif isinstance(symbols_config, str):
        stock_pool = FileStockPool(symbols_config)
    else:
        raise ValueError("Invalid symbols config")

    strategy_config = config.get("strategy", {})
    if isinstance(strategy_config, str):
        strategy_name = strategy_config
        strategy_params = config.get("strategy_params", {})
    else:
        strategy_name = strategy_config.get("name", "macd")
        strategy_params = strategy_config.get("params", {})

    strategy = create_strategy(strategy_name, **strategy_params)

    cash_config = config.get("cash", {})
    fee_config = cash_config.get("fee", {})

    backtest_config = BacktestConfig()
    backtest_config.initial_capital = cash_config.get("initial_capital", 1000000)
    backtest_config.commission_rate = fee_config.get("commission_rate", 0.0003)
    backtest_config.slippage = fee_config.get("slippage", 0.0)
    backtest_config.stamp_duty = fee_config.get("stamp_duty", 0.001)
    backtest_config.stock_pool = stock_pool
    backtest_config.strategy = strategy

    date_config = config.get("date", {})
    backtest_config.start_date = date_config.get("start", config.get("start_date", "2023-01-01"))
    backtest_config.end_date = date_config.get("end", config.get("end_date", "2024-01-01"))

    backtest_opts = config.get("backtest", {})
    backtest_config.position_size = backtest_opts.get("position_size", config.get("position_size", 1.0))
    backtest_config.max_positions = backtest_opts.get("max_positions", config.get("max_positions", 10))
    backtest_config.rebalance_days = backtest_opts.get("rebalance_days", config.get("rebalance_days", 0))

    backtest = Backtest()
    result = backtest.run(config=backtest_config, market_data=market_data)

    benchmarks = config.get("benchmark", [])
    if benchmarks:
        result.benchmark_data = fetch_benchmarks(market_data, benchmarks, 
            backtest_config.start_date, backtest_config.end_date,
            result.initial_capital)

    if config.get("work_dir"):
        result_path = save_result(config, result)
        print(f"\nResult saved to: {result_path}")
        
        cache_path = save_cache(config, provider)
        trades = result.trades if hasattr(result, 'trades') else []
        if trades:
            import csv
            with open(cache_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "symbol", "action", "price", "shares", "amount", "commission"])
                for trade in trades:
                    writer.writerow([
                        trade.date,
                        trade.symbol,
                        trade.action,
                        f"{trade.price:.2f}",
                        trade.shares,
                        f"{trade.amount:.2f}" if hasattr(trade, 'amount') else "",
                        f"{trade.commission:.2f}" if hasattr(trade, 'commission') else ""
                    ])
            print(f"Cache saved to: {cache_path}")

    return result
