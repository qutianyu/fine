from typing import Dict
import numpy as np
from ..base import Indicator


class VR(Indicator):
    name = "VR"

    def compute(
        self, close: np.ndarray, volume: np.ndarray, period: int = 26
    ) -> Dict[str, np.ndarray]:
        vr = np.zeros(len(close))

        for i in range(period - 1, len(close)):
            up_vol = 0.0
            down_vol = 0.0

            for j in range(i - period + 1, i + 1):
                if j > 0 and close[j] > close[j - 1]:
                    up_vol += volume[j]
                else:
                    down_vol += volume[j]

            if down_vol != 0:
                vr[i] = (up_vol / down_vol) * 100
            else:
                vr[i] = 100

        return {"vr": vr, "signal": self._get_signal(vr)}

    @staticmethod
    def _get_signal(vr: np.ndarray) -> np.ndarray:
        signal = np.full(len(vr), "hold")
        for i in range(1, len(vr)):
            if vr[i] < 40:
                signal[i] = "oversold"
            elif vr[i] > 150:
                signal[i] = "overbought"
            elif vr[i] > 100:
                signal[i] = "bullish"
            elif vr[i] < 100:
                signal[i] = "bearish"
        return signal
