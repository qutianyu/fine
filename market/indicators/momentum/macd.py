from typing import Dict
import numpy as np
from ..base import Indicator
from ..trend import EMA


class MACD(Indicator):
    name = "MACD"

    def compute(
        self, data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, np.ndarray]:
        ema = EMA()
        ema_fast = ema.compute(data, fast)
        ema_slow = ema.compute(data, slow)

        dif = ema_fast - ema_slow
        dea = ema.compute(dif, signal)
        macd = (dif - dea) * 2

        return {"dif": dif, "dea": dea, "macd": macd, "signal": self._get_signal(macd)}

    @staticmethod
    def _get_signal(macd: np.ndarray) -> np.ndarray:
        signal = np.full(len(macd), "hold")
        for i in range(1, len(macd)):
            if macd[i] > 0 and macd[i - 1] <= 0:
                signal[i] = "gold_cross"
            elif macd[i] < 0 and macd[i - 1] >= 0:
                signal[i] = "death_cross"
        return signal
