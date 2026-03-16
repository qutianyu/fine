from typing import Dict

import numpy as np

from ..base import Indicator


class RSI(Indicator):
    name = "RSI"

    def compute(self, data: np.ndarray, period: int = 14) -> Dict[str, np.ndarray]:
        if not isinstance(period, int):
            period = 14
        delta = np.diff(data)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))

        avg_gain[period] = np.mean(gain[:period])
        avg_loss[period] = np.mean(loss[:period])

        for i in range(period + 1, len(data)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i - 1]) / period

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        rsi[:period] = 50

        return {"rsi": rsi, "signal": self._get_signal(rsi)}

    @staticmethod
    def _get_signal(rsi: np.ndarray, overbought: float = 70, oversold: float = 30) -> np.ndarray:
        signal = np.full(len(rsi), "hold")
        for i in range(1, len(rsi)):
            if rsi[i] < oversold and rsi[i - 1] >= oversold:
                signal[i] = "oversold"
            elif rsi[i] > overbought and rsi[i - 1] <= overbought:
                signal[i] = "overbought"
        return signal
