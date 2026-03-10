from typing import Dict
import numpy as np
from ..base import Indicator


class DonchianChannel(Indicator):
    name = "DONCHIAN"

    def compute(
        self, high: np.ndarray, low: np.ndarray, period: int = 20
    ) -> Dict[str, np.ndarray]:
        upper = np.zeros(len(high))
        middle = np.zeros(len(high))
        lower = np.zeros(len(low))

        for i in range(period - 1, len(high)):
            upper[i] = np.max(high[i - period + 1 : i + 1])
            lower[i] = np.min(low[i - period + 1 : i + 1])
            middle[i] = (upper[i] + lower[i]) / 2

        return {"upper": upper, "middle": middle, "lower": lower}
