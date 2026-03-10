from typing import Dict
import numpy as np
from ..base import Indicator
from .rsi import RSI


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
