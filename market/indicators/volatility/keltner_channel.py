from typing import Dict
import numpy as np
from ..base import Indicator
from ..trend import EMA


class KeltnerChannel(Indicator):
    name = "KC"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 20,
        multiplier: float = 2.0,
    ) -> Dict[str, np.ndarray]:
        ema = EMA().compute(close, period)

        tr = np.zeros(len(close))
        for i in range(1, len(close)):
            h_l = high[i] - low[i]
            h_c = abs(high[i] - close[i - 1])
            l_c = abs(low[i] - close[i - 1])
            tr[i] = max(h_l, h_c, l_c)

        atr = np.zeros(len(close))
        atr[period - 1] = np.mean(tr[1:period])
        for i in range(period, len(close)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        upper = ema + multiplier * atr
        lower = ema - multiplier * atr

        return {"upper": upper, "middle": ema, "lower": lower, "atr": atr}
