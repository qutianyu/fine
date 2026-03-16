from typing import Dict, List

import numpy as np

from ..base import Indicator


class MA(Indicator):
    name = "MA"

    def compute(self, data: np.ndarray, period: int = 20) -> np.ndarray:
        period = 20 if not isinstance(period, int) else period
        period = min(period, len(data))
        result = np.full(len(data), np.nan)
        result[period - 1 :] = np.convolve(data, np.ones(period) / period, mode="valid")
        return result
