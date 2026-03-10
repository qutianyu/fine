from typing import Dict
import numpy as np
from ..base import Indicator


class WilliamsAD(Indicator):
    name = "WAD"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
    ) -> Dict[str, np.ndarray]:
        wad = np.zeros(len(close))

        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                change = close[i] - min(close[i - 1], low[i])
            elif close[i] < close[i - 1]:
                change = close[i] - max(close[i - 1], high[i])
            else:
                change = 0

            wad[i] = wad[i - 1] + change * volume[i]

        return {"wad": wad, "signal": self._get_signal(wad)}

    @staticmethod
    def _get_signal(wad: np.ndarray) -> np.ndarray:
        signal = np.full(len(wad), "hold")
        for i in range(1, len(wad)):
            if wad[i] > wad[i - 1]:
                signal[i] = "accumulation"
            elif wad[i] < wad[i - 1]:
                signal[i] = "distribution"
        return signal
