from typing import Dict
import numpy as np
from .base import Indicator


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


class VWAP(Indicator):
    name = "VWAP"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
    ) -> np.ndarray:
        typical_price = (high + low + close) / 3
        vwap = np.zeros(len(close))

        cumsum = 0
        vol_sum = 0
        for i in range(len(close)):
            cumsum += typical_price[i] * volume[i]
            vol_sum += volume[i]
            vwap[i] = cumsum / (vol_sum + 1e-10)

        return vwap


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
