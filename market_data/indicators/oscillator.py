from typing import Dict
import numpy as np
from .base import Indicator
from .trend import MA, EMA


class WR(Indicator):
    name = "WR"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> Dict[str, np.ndarray]:
        wr = np.full(len(close), -50.0)
        wr_buy = np.full(len(close), -50.0)

        for i in range(period - 1, len(close)):
            high_n = high[i - period + 1 : i + 1]
            low_n = low[i - period + 1 : i + 1]

            highest = np.max(high_n)
            lowest = np.min(low_n)

            if highest != lowest:
                wr[i] = -((highest - close[i]) / (highest - lowest)) * 100

            if i >= period * 2 - 2:
                high_2n = high[i - period * 2 + 2 : i + 1]
                low_2n = low[i - period * 2 + 2 : i + 1]
                highest_2 = np.max(high_2n)
                lowest_2 = np.min(low_2n)
                if highest_2 != lowest_2:
                    wr_buy[i] = -((highest_2 - close[i]) / (highest_2 - lowest_2)) * 100

        return {"wr": wr, "wr_buy": wr_buy, "signal": self._get_signal(wr)}

    @staticmethod
    def _get_signal(
        wr: np.ndarray, overbought: float = -20, oversold: float = -80
    ) -> np.ndarray:
        signal = np.full(len(wr), "hold")
        for i in range(1, len(wr)):
            if wr[i] < oversold and wr[i - 1] >= oversold:
                signal[i] = "oversold"
            elif wr[i] > overbought and wr[i - 1] <= overbought:
                signal[i] = "overbought"
        return signal


class CCI(Indicator):
    name = "CCI"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
    ) -> Dict[str, np.ndarray]:
        tp = (high + low + close) / 3
        cci = np.zeros(len(close))

        for i in range(period - 1, len(close)):
            sma = np.mean(tp[i - period + 1 : i + 1])
            mean_deviation = np.mean(np.abs(tp[i - period + 1 : i + 1] - sma))

            if mean_deviation != 0:
                cci[i] = (tp[i] - sma) / (0.015 * mean_deviation)

        return {"cci": cci, "signal": self._get_signal(cci)}

    @staticmethod
    def _get_signal(cci: np.ndarray) -> np.ndarray:
        signal = np.full(len(cci), "hold")
        for i in range(1, len(cci)):
            if cci[i] < -100 and cci[i - 1] >= -100:
                signal[i] = "oversold"
            elif cci[i] > 100 and cci[i - 1] <= 100:
                signal[i] = "overbought"
            elif cci[i] > 100:
                signal[i] = "strong_up"
            elif cci[i] < -100:
                signal[i] = "strong_down"
        return signal


class BIAS(Indicator):
    name = "BIAS"

    def compute(self, data: np.ndarray, period: int = 6) -> Dict[str, np.ndarray]:
        ma = MA().compute(data, period)
        bias = np.zeros(len(data))

        for i in range(period - 1, len(data)):
            if ma[i] != 0:
                bias[i] = ((data[i] - ma[i]) / ma[i]) * 100

        return {"bias": bias, "signal": self._get_signal(bias)}

    @staticmethod
    def _get_signal(bias: np.ndarray) -> np.ndarray:
        signal = np.full(len(bias), "hold")
        for i in range(1, len(bias)):
            if bias[i] < -10 and bias[i - 1] >= -10:
                signal[i] = "oversold"
            elif bias[i] > 10 and bias[i - 1] <= 10:
                signal[i] = "overbought"
            elif abs(bias[i]) < 3:
                signal[i] = "neutral"
        return signal


class CR(Indicator):
    name = "CR"

    def compute(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 26
    ) -> Dict[str, np.ndarray]:
        cr = np.zeros(len(close))
        cr_ma = np.zeros(len(close))

        for i in range(period - 1, len(close)):
            balance = (high[i] + low[i] + close[i]) / 3
            pressure = 2 * close[i] - low[i]
            support = 2 * close[i] - high[i]

            if balance != support:
                cr[i] = ((pressure - balance) / (balance - support)) * 100

        for i in range(period - 1, len(close)):
            cr_ma[i] = np.mean(cr[i - period + 1 : i + 1])

        return {"cr": cr, "cr_ma": cr_ma, "signal": self._get_signal(cr, cr_ma)}

    @staticmethod
    def _get_signal(cr: np.ndarray, cr_ma: np.ndarray) -> np.ndarray:
        signal = np.full(len(cr), "hold")
        for i in range(1, len(cr)):
            if cr[i] < cr_ma[i] and cr[i - 1] >= cr_ma[i - 1]:
                signal[i] = "death_cross"
            elif cr[i] > cr_ma[i] and cr[i - 1] <= cr_ma[i - 1]:
                signal[i] = "gold_cross"
            elif cr[i] > 150:
                signal[i] = "overbought"
            elif cr[i] < 50:
                signal[i] = "oversold"
        return signal


class ARBR(Indicator):
    name = "ARBR"

    def compute(
        self,
        open: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 26,
    ) -> Dict[str, np.ndarray]:
        ar = np.zeros(len(close))
        br = np.zeros(len(close))
        ar_ma = np.zeros(len(close))
        br_ma = np.zeros(len(close))

        for i in range(period - 1, len(close)):
            sum_higher = 0.0
            sum_lower = 0.0

            for j in range(i - period + 1, i + 1):
                if j > 0:
                    sum_higher += high[j] - open[j]
                    sum_lower += open[j] - low[j]

            if sum_lower != 0:
                ar[i] = (sum_higher / sum_lower) * 100
            else:
                ar[i] = 100

            sum_up = 0.0
            sum_down = 0.0

            for j in range(i - period + 1, i + 1):
                if j > 0:
                    if close[j] > close[j - 1]:
                        sum_up += close[j] - close[j - 1]
                    elif close[j] < close[j - 1]:
                        sum_down += close[j - 1] - close[j]

            if sum_down != 0:
                br[i] = (sum_up / sum_down) * 100
            else:
                br[i] = 100

            ar_ma[i] = np.mean(ar[i - period + 1 : i + 1])
            br_ma[i] = np.mean(br[i - period + 1 : i + 1])

        return {
            "ar": ar,
            "br": br,
            "ar_ma": ar_ma,
            "br_ma": br_ma,
            "signal": self._get_signal(ar, br, ar_ma, br_ma),
        }

    @staticmethod
    def _get_signal(
        ar: np.ndarray, br: np.ndarray, ar_ma: np.ndarray, br_ma: np.ndarray
    ) -> np.ndarray:
        signal = np.full(len(ar), "hold")
        for i in range(1, len(ar)):
            if ar[i] < 50 and br[i] < 50:
                signal[i] = "oversold"
            elif ar[i] > 150 and br[i] > 150:
                signal[i] = "overbought"
            elif ar[i] > br[i] and ar[i - 1] <= br[i - 1]:
                signal[i] = "gold_cross"
            elif ar[i] < br[i] and ar[i - 1] >= br[i - 1]:
                signal[i] = "death_cross"
        return signal


class PSY(Indicator):
    name = "PSY"

    def compute(self, close: np.ndarray, period: int = 12) -> Dict[str, np.ndarray]:
        psy = np.zeros(len(close))

        for i in range(period - 1, len(close)):
            up_count = 0
            for j in range(i - period + 1, i + 1):
                if j > 0 and close[j] > close[j - 1]:
                    up_count += 1
            psy[i] = (up_count / period) * 100

        return {"psy": psy, "signal": self._get_signal(psy)}

    @staticmethod
    def _get_signal(psy: np.ndarray) -> np.ndarray:
        signal = np.full(len(psy), "hold")
        for i in range(1, len(psy)):
            if psy[i] < 25 and psy[i - 1] >= 25:
                signal[i] = "oversold"
            elif psy[i] > 75 and psy[i - 1] <= 75:
                signal[i] = "overbought"
            elif psy[i] > 50:
                signal[i] = "bullish"
            elif psy[i] < 50:
                signal[i] = "bearish"
        return signal


class DMI(Indicator):
    name = "DMI"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14,
        adx_period: int = 14,
    ) -> Dict[str, np.ndarray]:
        tr = np.zeros(len(close))
        plus_dm = np.zeros(len(close))
        minus_dm = np.zeros(len(close))

        for i in range(1, len(close)):
            high_diff = high[i] - high[i - 1]
            low_diff = low[i - 1] - low[i]

            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )

            if high_diff > low_diff and high_diff > 0:
                plus_dm[i] = high_diff
            if low_diff > high_diff and low_diff > 0:
                minus_dm[i] = low_diff

        tr_sum = np.zeros(len(close))
        plus_dm_sum = np.zeros(len(close))
        minus_dm_sum = np.zeros(len(close))

        tr_sum[period] = np.sum(tr[1 : period + 1])
        plus_dm_sum[period] = np.sum(plus_dm[1 : period + 1])
        minus_dm_sum[period] = np.sum(minus_dm[1 : period + 1])

        for i in range(period + 1, len(close)):
            tr_sum[i] = tr_sum[i - 1] - tr_sum[i - 1] / period + tr[i]
            plus_dm_sum[i] = (
                plus_dm_sum[i - 1] - plus_dm_sum[i - 1] / period + plus_dm[i]
            )
            minus_dm_sum[i] = (
                minus_dm_sum[i - 1] - minus_dm_sum[i - 1] / period + minus_dm[i]
            )

        plus_di = np.zeros(len(close))
        minus_di = np.zeros(len(close))

        for i in range(period, len(close)):
            if tr_sum[i] > 0:
                plus_di[i] = (plus_dm_sum[i] / tr_sum[i]) * 100
                minus_di[i] = (minus_dm_sum[i] / tr_sum[i]) * 100

        dx = np.zeros(len(close))
        for i in range(period, len(close)):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx[i] = abs(plus_di[i] - minus_di[i]) / di_sum * 100

        adx = np.zeros(len(close))
        adx[period * 2] = np.mean(dx[period : period * 2])
        for i in range(period * 2 + 1, len(close)):
            adx[i] = (adx[i - 1] * (adx_period - 1) + dx[i]) / adx_period

        adxr = np.zeros(len(close))
        for i in range(period * 2 + adx_period - 1, len(close)):
            adxr[i] = (adx[i - adx_period + 1] + adx[i]) / 2

        return {
            "plus_di": plus_di,
            "minus_di": minus_di,
            "adx": adx,
            "adxr": adxr,
            "signal": self._get_signal(plus_di, minus_di, adx),
        }

    @staticmethod
    def _get_signal(
        plus_di: np.ndarray, minus_di: np.ndarray, adx: np.ndarray
    ) -> np.ndarray:
        signal = np.full(len(plus_di), "hold")
        for i in range(1, len(plus_di)):
            if plus_di[i] > minus_di[i] and plus_di[i - 1] <= minus_di[i - 1]:
                signal[i] = "gold_cross"
            elif plus_di[i] < minus_di[i] and plus_di[i - 1] >= minus_di[i - 1]:
                signal[i] = "death_cross"
            elif adx[i] > 25:
                signal[i] = "strong_trend"
        return signal


class UltimateOscillator(Indicator):
    name = "ULTIMATE"

    def compute(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period1: int = 7,
        period2: int = 14,
        period3: int = 28,
    ) -> Dict[str, np.ndarray]:
        bp = np.zeros(len(close))
        tr = np.zeros(len(close))

        for i in range(1, len(close)):
            bp[i] = close[i] - min(low[i], close[i - 1])
            tr[i] = max(high[i], close[i - 1]) - min(low[i], close[i - 1])

        avg1 = np.zeros(len(close))
        avg2 = np.zeros(len(close))
        avg3 = np.zeros(len(close))

        for i in range(period1, len(close)):
            avg1[i] = (
                np.sum(bp[i - period1 + 1 : i + 1])
                / (np.sum(tr[i - period1 + 1 : i + 1]) + 1e-10)
                * 100
            )

        for i in range(period2, len(close)):
            avg2[i] = (
                np.sum(bp[i - period2 + 1 : i + 1])
                / (np.sum(tr[i - period2 + 1 : i + 1]) + 1e-10)
                * 100
            )

        for i in range(period3, len(close)):
            avg3[i] = (
                np.sum(bp[i - period3 + 1 : i + 1])
                / (np.sum(tr[i - period3 + 1 : i + 1]) + 1e-10)
                * 100
            )

        uo = np.zeros(len(close))
        for i in range(period3, len(close)):
            uo[i] = (avg1[i] * 4 + avg2[i] * 2 + avg3[i]) / (4 + 2 + 1)

        return {"uo": uo, "signal": self._get_signal(uo)}

    @staticmethod
    def _get_signal(uo: np.ndarray) -> np.ndarray:
        signal = np.full(len(uo), "hold")
        for i in range(1, len(uo)):
            if uo[i] < 30 and uo[i - 1] >= 30:
                signal[i] = "oversold"
            elif uo[i] > 70 and uo[i - 1] <= 70:
                signal[i] = "overbought"
            elif uo[i] > 50:
                signal[i] = "bullish"
            else:
                signal[i] = "bearish"
        return signal


class DMA(Indicator):
    name = "DMA"

    def compute(
        self, data: np.ndarray, fast_period: int = 10, slow_period: int = 50
    ) -> Dict[str, np.ndarray]:
        ma_fast = MA().compute(data, fast_period)
        ma_slow = MA().compute(data, slow_period)

        dma = ma_fast - ma_slow
        ama = MA().compute(dma, fast_period)

        return {"dma": dma, "ama": ama, "signal": self._get_signal(dma, ama)}

    @staticmethod
    def _get_signal(dma: np.ndarray, ama: np.ndarray) -> np.ndarray:
        signal = np.full(len(dma), "hold")
        for i in range(1, len(dma)):
            if dma[i] > ama[i] and dma[i - 1] <= ama[i - 1]:
                signal[i] = "gold_cross"
            elif dma[i] < ama[i] and dma[i - 1] >= ama[i - 1]:
                signal[i] = "death_cross"
        return signal


class TRIX(Indicator):
    name = "TRIX"

    def compute(
        self, data: np.ndarray, period: int = 12, signal_period: int = 9
    ) -> Dict[str, np.ndarray]:
        ema1 = EMA().compute(data, period)
        ema2 = EMA().compute(ema1, period)
        ema3 = EMA().compute(ema2, period)

        trix = np.zeros(len(data))
        for i in range(1, len(data)):
            if ema3[i - 1] != 0:
                trix[i] = ((ema3[i] - ema3[i - 1]) / ema3[i - 1]) * 100

        signal_line = EMA().compute(trix, signal_period)

        return {"trix": trix, "signal": signal_line, "signal_line": signal_line}

    @staticmethod
    def _get_signal(trix: np.ndarray, signal: np.ndarray) -> np.ndarray:
        signal_arr = np.full(len(trix), "hold")
        for i in range(1, len(trix)):
            if trix[i] > signal[i] and trix[i - 1] <= signal[i - 1]:
                signal_arr[i] = "gold_cross"
            elif trix[i] < signal[i] and trix[i - 1] >= signal[i - 1]:
                signal_arr[i] = "death_cross"
            elif trix[i] > 0:
                signal_arr[i] = "bullish"
            elif trix[i] < 0:
                signal_arr[i] = "bearish"
        return signal_arr
