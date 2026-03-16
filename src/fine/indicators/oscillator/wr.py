from typing import Dict

import numpy as np

from ..base import Indicator


class WR(Indicator):
    name = "WR"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> Dict[str, np.ndarray]:
        wr = np.full(len(close), -50.0)
        wr_buy = np.full(len(close), -50.0)

        for i in range(period - 1, len(close)):
            high_n = high[i - period + 1 : i + 1]
            low_n = low[i - period + 1 : i + 1]

            highest = np.max(high_n)
            lowest = np.min(low_n)

            if highest != lowest:
                wr[i] = -((highest - close[i]) / (highest - lowest)) * 100

            if i >= period * 2 - 2:
                high_2n = high[i - period * 2 + 2 : i + 1]
                low_2n = low[i - period * 2 + 2 : i + 1]
                highest_2 = np.max(high_2n)
                lowest_2 = np.min(low_2n)
                if highest_2 != lowest_2:
                    wr_buy[i] = -((highest_2 - close[i]) / (highest_2 - lowest_2)) * 100

        return {"wr": wr, "wr_buy": wr_buy, "signal": self._get_signal(wr)}

    @staticmethod
    def _get_signal(wr: np.ndarray, overbought: float = -20, oversold: float = -80) -> np.ndarray:
        signal = np.full(len(wr), "hold")
        for i in range(1, len(wr)):
            if wr[i] < oversold and wr[i - 1] >= oversold:
                signal[i] = "oversold"
            elif wr[i] > overbought and wr[i - 1] <= overbought:
                signal[i] = "overbought"
        return signal
