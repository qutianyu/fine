from typing import Dict
import numpy as np
from .base import Indicator
from .trend import EMA


class MACD(Indicator):
    name = "MACD"

    def compute(
        self, data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, np.ndarray]:
        ema = EMA()
        ema_fast = ema.compute(data, fast)
        ema_slow = ema.compute(data, slow)

        dif = ema_fast - ema_slow
        dea = ema.compute(dif, signal)
        macd = (dif - dea) * 2

        return {"dif": dif, "dea": dea, "macd": macd, "signal": self._get_signal(macd)}

    @staticmethod
    def _get_signal(macd: np.ndarray) -> np.ndarray:
        signal = np.full(len(macd), "hold")
        for i in range(1, len(macd)):
            if macd[i] > 0 and macd[i - 1] <= 0:
                signal[i] = "gold_cross"
            elif macd[i] < 0 and macd[i - 1] >= 0:
                signal[i] = "death_cross"
        return signal


class KDJ(Indicator):
    name = "KDJ"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        n: int = 9,
        m1: int = 3,
        m2: int = 3,
    ) -> Dict[str, np.ndarray]:

        rsv = np.zeros(len(close))
        k = np.zeros(len(close))
        d = np.zeros(len(close))
        j = np.zeros(len(close))

        for i in range(n - 1, len(close)):
            high_n = high[i - n + 1 : i + 1]
            low_n = low[i - n + 1 : i + 1]

            rsv_n = (close[i] - np.min(low_n)) / (np.max(high_n) - np.min(low_n)) * 100
            rsv[i] = rsv_n

            if i == n - 1:
                k[i] = 50
                d[i] = 50
            else:
                k[i] = (m1 - 1) / m1 * k[i - 1] + 1 / m1 * rsv[i]
                d[i] = (m2 - 1) / m2 * d[i - 1] + 1 / m2 * k[i]

            j[i] = 3 * k[i] - 2 * d[i]

        return {"k": k, "d": d, "j": j, "signal": self._get_signal(k, d)}

    @staticmethod
    def _get_signal(k: np.ndarray, d: np.ndarray) -> np.ndarray:
        signal = np.full(len(k), "hold")
        for i in range(1, len(k)):
            if k[i] > d[i] and k[i - 1] <= d[i - 1]:
                signal[i] = "gold_cross"
            elif k[i] < d[i] and k[i - 1] >= d[i - 1]:
                signal[i] = "death_cross"
            elif k[i] > 80:
                signal[i] = "overbought"
            elif k[i] < 20:
                signal[i] = "oversold"
        return signal


class RSI(Indicator):
    name = "RSI"

    def compute(self, data: np.ndarray, period: int = 14) -> Dict[str, np.ndarray]:
        if not isinstance(period, int):
            period = 14
        delta = np.diff(data)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))

        avg_gain[period] = np.mean(gain[:period])
        avg_loss[period] = np.mean(loss[:period])

        for i in range(period + 1, len(data)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i - 1]) / period

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        rsi[:period] = 50

        return {"rsi": rsi, "signal": self._get_signal(rsi)}

    @staticmethod
    def _get_signal(
        rsi: np.ndarray, overbought: float = 70, oversold: float = 30
    ) -> np.ndarray:
        signal = np.full(len(rsi), "hold")
        for i in range(1, len(rsi)):
            if rsi[i] < oversold and rsi[i - 1] >= oversold:
                signal[i] = "oversold"
            elif rsi[i] > overbought and rsi[i - 1] <= overbought:
                signal[i] = "overbought"
        return signal


class StochRSI(Indicator):
    name = "STOCHRSI"

    def compute(
        self, data: np.ndarray, period: int = 14, k_period: int = 3, d_period: int = 3
    ) -> Dict[str, np.ndarray]:
        rsi_values = RSI().compute(data, period)["rsi"]

        stoch_rsi = np.zeros(len(data))
        k_line = np.zeros(len(data))
        d_line = np.zeros(len(data))

        for i in range(period - 1, len(data)):
            rsi_slice = rsi_values[i - period + 1 : i + 1]
            rsi_max = np.max(rsi_slice)
            rsi_min = np.min(rsi_slice)

            if rsi_max != rsi_min:
                stoch_rsi[i] = (rsi_values[i] - rsi_min) / (rsi_max - rsi_min) * 100
            else:
                stoch_rsi[i] = 50

        for i in range(period - 1, len(stoch_rsi)):
            k_slice = stoch_rsi[i - k_period + 1 : i + 1]
            k_line[i] = np.mean(k_slice) if len(k_slice) > 0 else stoch_rsi[i]

        for i in range(period - 1 + k_period - 1, len(d_line)):
            d_slice = k_line[i - d_period + 1 : i + 1]
            d_line[i] = np.mean(d_slice) if len(d_slice) > 0 else k_line[i]

        return {
            "stoch_rsi": stoch_rsi,
            "k": k_line,
            "d": d_line,
            "signal": self._get_signal(k_line, d_line),
        }

    @staticmethod
    def _get_signal(k_line: np.ndarray, d_line: np.ndarray) -> np.ndarray:
        signal = np.full(len(k_line), "hold")
        for i in range(1, len(k_line)):
            if k_line[i] > d_line[i] and k_line[i - 1] <= d_line[i - 1]:
                signal[i] = "gold_cross"
            elif k_line[i] < d_line[i] and k_line[i - 1] >= d_line[i - 1]:
                signal[i] = "death_cross"
            elif k_line[i] > 80:
                signal[i] = "overbought"
            elif k_line[i] < 20:
                signal[i] = "oversold"
        return signal
