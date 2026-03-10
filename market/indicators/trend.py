from typing import Dict, List
import numpy as np
from .base import Indicator


class MA(Indicator):
    name = "MA"

    def compute(self, data: np.ndarray, period: int = 20) -> np.ndarray:
        period = 20 if not isinstance(period, int) else period
        period = min(period, len(data))
        result = np.full(len(data), np.nan)
        result[period - 1 :] = np.convolve(data, np.ones(period) / period, mode="valid")
        return result


class EMA(Indicator):
    name = "EMA"

    def compute(self, data: np.ndarray, period: int = 12) -> np.ndarray:
        result = np.zeros(len(data))
        result[0] = data[0]
        multiplier = 2 / (period + 1)
        for i in range(1, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        return result


class BBI(Indicator):
    name = "BBI"

    def compute(self, data: np.ndarray, periods: List[int] = None) -> np.ndarray:
        if periods is None:
            periods = [3, 6, 12, 24]

        ma = MA()
        ma3 = ma.compute(data, periods[0])
        ma6 = ma.compute(data, periods[1])
        ma12 = ma.compute(data, periods[2])
        ma24 = ma.compute(data, periods[3])

        result = (ma3 + ma6 + ma12 + ma24) / 4
        return result


class SAR(Indicator):
    name = "SAR"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        af_start: float = 0.02,
        af_max: float = 0.2,
    ) -> Dict[str, np.ndarray]:
        sar = np.zeros(len(close))
        trend = np.zeros(len(close))
        ep = np.zeros(len(close))
        af = np.zeros(len(close))

        if close[1] > close[0]:
            trend[0] = 1
            sar[0] = low[0]
            ep[0] = high[0]
        else:
            trend[0] = -1
            sar[0] = high[0]
            ep[0] = low[0]

        af[0] = af_start

        for i in range(1, len(close)):
            if trend[i - 1] == 1:
                sar[i] = sar[i - 1] + af[i - 1] * (ep[i - 1] - sar[i - 1])

                if low[i] < sar[i]:
                    trend[i] = -1
                    sar[i] = ep[i - 1]
                    ep[i] = low[i]
                    af[i] = af_start
                else:
                    trend[i] = 1
                    if high[i] > ep[i - 1]:
                        ep[i] = high[i]
                        af[i] = min(af[i - 1] + af_start, af_max)
                    else:
                        ep[i] = ep[i - 1]
                        af[i] = af[i - 1]
            else:
                sar[i] = sar[i - 1] + af[i - 1] * (ep[i - 1] - sar[i - 1])

                if high[i] > sar[i]:
                    trend[i] = 1
                    sar[i] = ep[i - 1]
                    ep[i] = high[i]
                    af[i] = af_start
                else:
                    trend[i] = -1
                    if low[i] < ep[i - 1]:
                        ep[i] = low[i]
                        af[i] = min(af[i - 1] + af_start, af_max)
                    else:
                        ep[i] = ep[i - 1]
                        af[i] = af[i - 1]

        return {
            "sar": sar,
            "trend": trend,
            "signal": self._get_signal(sar, close, trend),
        }

    @staticmethod
    def _get_signal(
        sar: np.ndarray, close: np.ndarray, trend: np.ndarray
    ) -> np.ndarray:
        signal = np.full(len(sar), "hold")
        for i in range(1, len(sar)):
            if trend[i] == 1 and trend[i - 1] == -1:
                signal[i] = "buy"
            elif trend[i] == -1 and trend[i - 1] == 1:
                signal[i] = "sell"
            elif sar[i] < close[i]:
                signal[i] = "bullish"
            else:
                signal[i] = "bearish"
        return signal
