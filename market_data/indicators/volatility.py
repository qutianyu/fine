from typing import Dict
import numpy as np
from .base import Indicator
from .trend import EMA


class BollingerBands(Indicator):
    name = "BOLL"

    def compute(
        self, data: np.ndarray, period: int = 20, std_dev: float = 2.0
    ) -> Dict[str, np.ndarray]:
        if not isinstance(period, int):
            period = 20
        ma = EMA().compute(data, period)
        std = np.zeros(len(data))

        for i in range(period - 1, len(data)):
            std[i] = np.std(data[i - period + 1 : i + 1])

        upper = ma + std_dev * std
        lower = ma - std_dev * std

        return {
            "upper": upper,
            "middle": ma,
            "lower": lower,
            "bandwidth": (upper - lower) / ma,
            "percent": (data - lower) / (upper - lower + 1e-10),
        }


class ATR(Indicator):
    name = "ATR"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> np.ndarray:
        if not isinstance(period, int):
            period = 14
        tr = np.zeros(len(close))

        for i in range(1, len(close)):
            h_l = high[i] - low[i]
            h_c = abs(high[i] - close[i - 1])
            l_c = abs(low[i] - close[i - 1])
            tr[i] = max(h_l, h_c, l_c)

        atr = np.zeros(len(close))
        atr[period - 1] = np.mean(tr[1:period])
        for i in range(period, len(close)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        return atr


class KeltnerChannel(Indicator):
    name = "KC"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 20,
        multiplier: float = 2.0,
    ) -> Dict[str, np.ndarray]:
        ema = EMA().compute(close, period)

        tr = np.zeros(len(close))
        for i in range(1, len(close)):
            h_l = high[i] - low[i]
            h_c = abs(high[i] - close[i - 1])
            l_c = abs(low[i] - close[i - 1])
            tr[i] = max(h_l, h_c, l_c)

        atr = np.zeros(len(close))
        atr[period - 1] = np.mean(tr[1:period])
        for i in range(period, len(close)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        upper = ema + multiplier * atr
        lower = ema - multiplier * atr

        return {"upper": upper, "middle": ema, "lower": lower, "atr": atr}


class DonchianChannel(Indicator):
    name = "DONCHIAN"

    def compute(
        self, high: np.ndarray, low: np.ndarray, period: int = 20
    ) -> Dict[str, np.ndarray]:
        upper = np.zeros(len(high))
        middle = np.zeros(len(high))
        lower = np.zeros(len(low))

        for i in range(period - 1, len(high)):
            upper[i] = np.max(high[i - period + 1 : i + 1])
            lower[i] = np.min(low[i - period + 1 : i + 1])
            middle[i] = (upper[i] + lower[i]) / 2

        return {"upper": upper, "middle": middle, "lower": lower}
