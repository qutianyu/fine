import numpy as np
from ..base import Indicator


class EMA(Indicator):
    name = "EMA"

    def compute(self, data: np.ndarray, period: int = 12) -> np.ndarray:
        result = np.zeros(len(data))
        result[0] = data[0]
        multiplier = 2 / (period + 1)
        for i in range(1, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        return result
