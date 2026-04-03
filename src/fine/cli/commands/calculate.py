"""Calculate command - 计算技术指标/收益率/风险指标"""

import os
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd


INDICATOR_COLUMNS = {
    "kdj": ["k", "d", "j"],
    "macd": ["macd", "signal", "hist"],
    "rsi": ["rsi"],
    "wr": ["wr"],
    "atr": ["atr"],
    "obv": ["obv"],
    "mfi": ["mfi"],
    "cmf": ["cmf"],
    "vr": ["vr"],
}


def compute_returns(df: pd.DataFrame, col: str = "close") -> pd.DataFrame:
    """计算收益率"""
    result = df.copy()
    result["daily_return"] = df[col].pct_change() * 100
    result["cum_return"] = (1 + df[col].pct_change()).cumprod() - 1
    result["cum_return"] = result["cum_return"] * 100
    return result


def compute_rolling_stats(df: pd.DataFrame, col: str = "close", window: int = 20) -> pd.DataFrame:
    """计算滚动统计"""
    result = df.copy()
    result[f"rolling_mean_{window}"] = df[col].rolling(window=window).mean()
    result[f"rolling_std_{window}"] = df[col].rolling(window=window).std()
    result[f"rolling_max_{window}"] = df[col].rolling(window=window).max()
    result[f"rolling_min_{window}"] = df[col].rolling(window=window).min()
    return result


def compute_risk_metrics(
    df: pd.DataFrame, col: str = "close", risk_free_rate: float = 0.0
) -> pd.DataFrame:
    """计算风险指标"""
    result = df.copy()

    daily_returns = df[col].pct_change().dropna()

    if len(daily_returns) > 1:
        volatility = daily_returns.std() * np.sqrt(252) * 100
        result["annual_volatility"] = volatility
    else:
        result["annual_volatility"] = 0.0

    cumulative = (1 + daily_returns).cumprod()
    peak = cumulative.expanding(min_periods=1).max()
    drawdown = (cumulative - peak) / peak * 100
    result["max_drawdown"] = drawdown.min() if len(drawdown) > 0 else 0.0

    if len(daily_returns) > 1 and daily_returns.std() != 0:
        excess_return = daily_returns.mean() - risk_free_rate / 252
        sharpe = excess_return / daily_returns.std() * np.sqrt(252)
        result["sharpe_ratio"] = sharpe
    else:
        result["sharpe_ratio"] = 0.0

    return result


def calculate_portfolio_metrics(df: pd.DataFrame, risk_free_rate: float = 0.0):
    """计算组合整体指标"""
    metrics = {}

    daily_returns = df["close"].pct_change().dropna()

    if len(daily_returns) > 1:
        # 总收益率
        total_return = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
        metrics["total_return"] = total_return

        # 年化收益率
        n_days = len(df)
        annual_return = ((1 + total_return / 100) ** (252 / n_days) - 1) * 100
        metrics["annual_return"] = annual_return

        # 年化波动率
        volatility = daily_returns.std() * np.sqrt(252) * 100
        metrics["annual_volatility"] = volatility

        # 夏普比率
        excess_return = daily_returns.mean() - risk_free_rate / 252
        if daily_returns.std() != 0:
            sharpe = excess_return / daily_returns.std() * np.sqrt(252)
            metrics["sharpe_ratio"] = sharpe
        else:
            metrics["sharpe_ratio"] = 0.0

        # 最大回撤
        cumulative = (1 + daily_returns).cumprod()
        peak = cumulative.expanding(min_periods=1).max()
        drawdown = (cumulative - peak) / peak * 100
        metrics["max_drawdown"] = drawdown.min()

        # 胜率
        metrics["win_rate"] = (daily_returns > 0).sum() / len(daily_returns) * 100

    return metrics


def calculate_indicators(group: pd.DataFrame) -> pd.DataFrame:
    """计算技术指标"""
    from fine.indicators import TechnicalIndicators

    ti = TechnicalIndicators()
    result = group.copy()

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

    indicator_names = ["ma", "ema", "macd", "kdj", "rsi", "boll"]

    for ind_name in indicator_names:
        try:
            res = ti.compute(ind_name, ohlcv)
            if res is None:
                continue

            cols = INDICATOR_COLUMNS.get(ind_name, [])
            if isinstance(res, dict):
                for col in cols:
                    if col in res:
                        result[col] = res[col]
                    elif hasattr(res, col):
                        result[col] = getattr(res, col)
            elif hasattr(res, "values"):
                if len(cols) == 1:
                    result[cols[0]] = res.values
                else:
                    for i, col in enumerate(cols):
                        if i < res.shape[1]:
                            result[col] = res[:, i]
        except Exception as e:
            print(f"Warning: Failed to compute {ind_name} for {symbol}: {e}", file=sys.stderr)

    return result


def cmd_calculate(args) -> int:
    """计算技术指标、收益率或风险指标"""
    data_file = Path(args.data)
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")
    calc_type = args.type or "indicator"

    if not data_file.exists():
        print(f"Error: Data file not found: {data_file}", file=sys.stderr)
        return 1

    try:
        df = pd.read_csv(data_file)

        required_cols = {"symbol", "date", "open", "close", "high", "low", "volume"}
        if not required_cols.issubset(set(df.columns)):
            print(f"Error: CSV must contain columns: {required_cols}", file=sys.stderr)
            return 1

        symbols = df["symbol"].unique()
        symbol_str = ",".join(symbols) if len(symbols) <= 3 else f"{symbols[0]}等{len(symbols)}只"
        start_date = df["date"].min().replace("-", "")
        end_date = df["date"].max().replace("-", "")

        result_dfs = []

        for symbol, group in df.groupby("symbol"):
            group = group.sort_values("date").reset_index(drop=True)

            if calc_type == "indicator":
                result_group = calculate_indicators(group)
            elif calc_type == "returns":
                result_group = compute_returns(group)
            elif calc_type == "rolling":
                window = args.window or 20
                result_group = compute_rolling_stats(group, window=window)
            elif calc_type == "risk":
                risk_free_rate = args.risk_free_rate or 0.0
                result_group = compute_risk_metrics(group, risk_free_rate=risk_free_rate)
            elif calc_type == "all":
                result_group = group.copy()
                result_group = compute_returns(result_group)
                result_group = compute_rolling_stats(result_group, window=20)
                result_group = compute_risk_metrics(result_group, args.risk_free_rate or 0.0)
                result_group = calculate_indicators(result_group)
            else:
                print(f"Error: Unknown calculation type: {calc_type}", file=sys.stderr)
                return 1

            result_dfs.append(result_group)

        if not result_dfs:
            print("Error: No data after calculation", file=sys.stderr)
            return 1

        result_df = pd.concat(result_dfs, ignore_index=True)

        filename = f"{symbol_str}_{start_date}-{end_date}_{calc_type}.csv"
        result_file = result_dir / filename
        result_dir.mkdir(parents=True, exist_ok=True)

        result_df.to_csv(result_file, index=False)

        print(str(result_file))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
