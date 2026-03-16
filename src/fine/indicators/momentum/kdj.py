from typing import Dict

import numpy as np

from ..base import Indicator


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
