from typing import List
import numpy as np
from ..base import Indicator
from .ma import MA


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
