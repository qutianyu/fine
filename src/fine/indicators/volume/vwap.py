from typing import Dict

import numpy as np

from ..base import Indicator


class VWAP(Indicator):
    name = "VWAP"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
    ) -> np.ndarray:
        typical_price = (high + low + close) / 3
        vwap = np.zeros(len(close))

        cumsum = 0
        vol_sum = 0
        for i in range(len(close)):
            cumsum += typical_price[i] * volume[i]
            vol_sum += volume[i]
            vwap[i] = cumsum / (vol_sum + 1e-10)

        return vwap
