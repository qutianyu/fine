from typing import Dict

import numpy as np

from ..base import Indicator


class OBV(Indicator):
    name = "OBV"

    def compute(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        obv = np.zeros(len(close))
        obv[0] = volume[0]

        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                obv[i] = obv[i - 1] + volume[i]
            elif close[i] < close[i - 1]:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]

        return obv
