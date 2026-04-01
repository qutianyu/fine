from typing import Any, Dict

from fine.indicators import TechnicalIndicators
from fine.strategies.data import Data


class Indicators:
    """指标计算封装类

    提供统一的指标计算接口，支持按需计算和缓存。

    Usage:
        def compute(self, portfolio, symbol, data: Data, indicators, risk):
            # 使用 Data 对象计算指标
            rsi_result = indicators.compute('RSI', data)
            rsi = rsi_result.get('rsi', 50)

            macd_result = indicators.compute('MACD', data)
    """

    def __init__(self, symbol: str = ""):
        """初始化指标计算器

        Args:
            symbol: 股票代码
        """
        self._symbol = symbol
        self._ti = TechnicalIndicators()
        self._cache: Dict[str, Any] = {}

    def compute(self, name: str, data: Data, **kwargs) -> Dict[str, Any]:
        """计算指标

        Args:
            name: 指标名称 (如 'RSI', 'MACD', 'MA' 等)
            data: Data 对象，包含 date, period, df
            **kwargs: 指标参数 (如 period=14, fast=12 等)

        Returns:
            Dict: 指标结果字典，包含当前日期的指标值
        """
        df = data.df
        date = data.date

        if df is None or len(df) < 20:
            return {name.lower(): None}

        if "date" in df.columns:
            df = df[df["date"] <= date].copy()
            if len(df) < 20:
                return {name.lower(): None}

        close = df["close"].values

        if "high" in df.columns:
            high = df["high"].values
        else:
            high = close

        if "low" in df.columns:
            low = df["low"].values
        else:
            low = close

        name_upper = name.upper()

        if name_upper == "RSI":
            period = kwargs.get("period", 14)
            result = self._ti.compute("RSI", close, period=period)
            if hasattr(result, "__len__") and not isinstance(result, dict):
                return {"rsi": result[-1] if len(result) > 0 else None}
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, "__len__") and len(v) > 0:
                        result[k] = v[-1]
            return result

        elif name_upper == "MACD":
            fast = kwargs.get("fast", 12)
            slow = kwargs.get("slow", 26)
            signal = kwargs.get("signal", 9)
            result = self._ti.compute("MACD", close, fast=fast, slow=slow, signal=signal)
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, "__len__") and len(v) > 0:
                        result[k] = v[-1]
            return result

        elif name_upper == "MA":
            period = kwargs.get("period", 5)
            result = self._ti.compute("MA", close, period=period)
            if hasattr(result, "__len__") and not isinstance(result, dict):
                return {"ma": result[-1] if len(result) > 0 else None}
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, "__len__") and len(v) > 0:
                        result[k] = v[-1]
            return result

        elif name_upper == "EMA":
            period = kwargs.get("period", 12)
            result = self._ti.compute("EMA", close, period=period)
            if hasattr(result, "__len__") and not isinstance(result, dict):
                return {"ema": result[-1] if len(result) > 0 else None}
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, "__len__") and len(v) > 0:
                        result[k] = v[-1]
            return result

        elif name_upper == "KDJ":
            n = kwargs.get("n", 9)
            m1 = kwargs.get("m1", 3)
            m2 = kwargs.get("m2", 3)
            result = self._ti.compute("KDJ", high, low, close, n=n, m1=m1, m2=m2)
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, "__len__") and len(v) > 0:
                        result[k] = v[-1]
            return result

        elif name_upper == "BOLL" or name_upper == "BOLLINGER":
            period = kwargs.get("period", 20)
            std = kwargs.get("std", 2.0)
            result = self._ti.compute("BOLL", close, period=period, std=std)
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, "__len__") and len(v) > 0:
                        result[k] = v[-1]
            return result

        elif name_upper == "DMI":
            period = kwargs.get("period", 14)
            result = self._ti.compute("DMI", high, low, close, period=period)
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(v, "__len__") and len(v) > 0:
                        result[k] = v[-1]
            return result

        elif name_upper == "ATR":
            period = kwargs.get("period", 14)
            result = self._ti.compute("ATR", high, low, close, period=period)
            if hasattr(result, "__len__"):
                return {"atr": result[-1] if len(result) > 0 else None}
            return result

        elif name_upper == "WR" or name_upper == "WILLIAMS_R":
            period = kwargs.get("period", 14)
            result = self._ti.compute("WR", high, low, close, period=period)
            return result if isinstance(result, dict) else {"wr": result}

        elif name_upper == "CCI":
            period = kwargs.get("period", 14)
            result = self._ti.compute("CCI", high, low, close, period=period)
            return result if isinstance(result, dict) else {"cci": result}

        elif name_upper == "OBV":
            volume = df["volume"].values
            result = self._ti.compute("OBV", close, volume)
            return result if isinstance(result, dict) else {"obv": result}

        elif name_upper == "BBI":
            result = self._ti.compute("BBI", close)
            if hasattr(result, "__len__") and not isinstance(result, dict):
                return {"bbi": result}
            return result if isinstance(result, dict) else {"bbi": result}

        else:
            result = self._ti.compute(name, close, **kwargs)
            return result if isinstance(result, dict) else {name.lower(): result}
