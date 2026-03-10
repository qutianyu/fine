from typing import Dict
import numpy as np
from ..base import Indicator


class CMF(Indicator):
    name = "CMF"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        period: int = 20,
    ) -> Dict[str, np.ndarray]:
        cmf = np.zeros(len(close))

        money_flow_multiplier = np.zeros(len(close))
        money_flow_volume = np.zeros(len(close))

        for i in range(len(close)):
            high_low_range = high[i] - low[i]
            if high_low_range != 0:
                money_flow_multiplier[i] = (
                    (close[i] - low[i]) - (high[i] - close[i])
                ) / high_low_range
            else:
                money_flow_multiplier[i] = 0
            money_flow_volume[i] = money_flow_multiplier[i] * volume[i]

        for i in range(period - 1, len(close)):
            flow_sum = np.sum(money_flow_volume[i - period + 1 : i + 1])
            vol_sum = np.sum(volume[i - period + 1 : i + 1])
            if vol_sum != 0:
                cmf[i] = flow_sum / vol_sum

        return {"cmf": cmf, "signal": self._get_signal(cmf)}

    @staticmethod
    def _get_signal(cmf: np.ndarray) -> np.ndarray:
        signal = np.full(len(cmf), "hold")
        for i in range(1, len(cmf)):
            if cmf[i] > 0.1:
                signal[i] = "strong_accumulation"
            elif cmf[i] < -0.1:
                signal[i] = "strong_distribution"
            elif cmf[i] > 0:
                signal[i] = "accumulation"
            else:
                signal[i] = "distribution"
        return signal
