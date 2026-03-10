from typing import Dict
import numpy as np
from ..base import Indicator


class MFI(Indicator):
    name = "MFI"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        period: int = 14,
    ) -> Dict[str, np.ndarray]:
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume

        positive_flow = np.zeros(len(close))
        negative_flow = np.zeros(len(close))

        for i in range(1, len(close)):
            if typical_price[i] > typical_price[i - 1]:
                positive_flow[i] = money_flow[i]
            elif typical_price[i] < typical_price[i - 1]:
                negative_flow[i] = money_flow[i]

        mfi = np.zeros(len(close))

        for i in range(period, len(close)):
            positive_sum = np.sum(positive_flow[i - period + 1 : i + 1])
            negative_sum = np.sum(negative_flow[i - period + 1 : i + 1])

            if negative_sum != 0:
                money_ratio = positive_sum / negative_sum
                mfi[i] = 100 - (100 / (1 + money_ratio))
            else:
                mfi[i] = 100

        return {"mfi": mfi, "signal": self._get_signal(mfi)}

    @staticmethod
    def _get_signal(
        mfi: np.ndarray, overbought: float = 80, oversold: float = 20
    ) -> np.ndarray:
        signal = np.full(len(mfi), "hold")
        for i in range(1, len(mfi)):
            if mfi[i] < oversold and mfi[i - 1] >= oversold:
                signal[i] = "oversold"
            elif mfi[i] > overbought and mfi[i - 1] <= overbought:
                signal[i] = "overbought"
            elif mfi[i] > 50:
                signal[i] = "bullish"
            else:
                signal[i] = "bearish"
        return signal
