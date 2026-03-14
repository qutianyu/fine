from typing import Dict, List, Union
from .base import Indicator, IndicatorResult
from .trend import MA, EMA, BBI, SAR
from .momentum import MACD, KDJ, RSI, StochRSI
from .volatility import BollingerBands, ATR, KeltnerChannel, DonchianChannel
from .volume import OBV, VWAP, MFI, WilliamsAD, CMF, VR
from .oscillator.wr import WR
from .trend.ma import MA
from .trend.ema import EMA
from .trend.bbi import BBI
from .trend.sar import SAR
from .momentum import MACD, KDJ, RSI, StochRSI
from .volatility import BollingerBands, ATR, KeltnerChannel, DonchianChannel
from .volume import OBV, VWAP, MFI, WilliamsAD, CMF, VR
import numpy as np


class IndicatorRegistry:
    _indicators: Dict[str, type] = {}

    @classmethod
    def register(cls, indicator_class: type):
        if issubclass(indicator_class, Indicator):
            cls._indicators[indicator_class.name.lower()] = indicator_class
        return indicator_class

    @classmethod
    def get(cls, name: str) -> Indicator:
        name = name.lower()
        if name not in cls._indicators:
            raise ValueError(
                f"Unknown indicator: {name}. Available: {list(cls._indicators.keys())}"
            )
        return cls._indicators[name]()

    @classmethod
    def list_indicators(cls) -> List[str]:
        return list(cls._indicators.keys())


IndicatorRegistry.register(MA)
IndicatorRegistry.register(EMA)
IndicatorRegistry.register(BBI)
IndicatorRegistry.register(SAR)
IndicatorRegistry.register(MACD)
IndicatorRegistry.register(KDJ)
IndicatorRegistry.register(RSI)
IndicatorRegistry.register(StochRSI)
IndicatorRegistry.register(BollingerBands)
IndicatorRegistry.register(ATR)
IndicatorRegistry.register(KeltnerChannel)
IndicatorRegistry.register(DonchianChannel)
IndicatorRegistry.register(OBV)
IndicatorRegistry.register(VWAP)
IndicatorRegistry.register(MFI)
IndicatorRegistry.register(WilliamsAD)
IndicatorRegistry.register(CMF)
IndicatorRegistry.register(VR)
IndicatorRegistry.register(WR)


class TechnicalIndicators:
    def __init__(self):
        self._custom_indicators: Dict[str, Indicator] = {}

    @staticmethod
    def list_indicators() -> List[str]:
        return IndicatorRegistry.list_indicators()

    @staticmethod
    def get_indicator(name: str) -> Indicator:
        return IndicatorRegistry.get(name)

    def register_custom(self, name: str, indicator: Indicator):
        self._custom_indicators[name.lower()] = indicator

    def compute(self, name: str, data: Union[np.ndarray, Dict], **params):
        def to_scalar(v):
            if isinstance(v, np.ndarray):
                if v.size == 1:
                    return v.item()
                return v
            return v

        clean_params = {k: to_scalar(v) for k, v in params.items()}

        if name.lower() in self._custom_indicators:
            return self._custom_indicators[name.lower()].compute(data, **clean_params)

        indicator = IndicatorRegistry.get(name)

        if isinstance(data, dict):
            if name.upper() == "MACD":
                return indicator.compute(data["close"], **clean_params)
            elif name.upper() == "KDJ":
                return indicator.compute(
                    data["high"], data["low"], data["close"], **clean_params
                )
            elif name.upper() in ["BOLL", "ATR", "VWAP", "CR", "SAR", "KC", "KELTNER"]:
                return indicator.compute(
                    data["high"], data["low"], data["close"], **clean_params
                )
            elif name.upper() == "OBV":
                return indicator.compute(data["close"], data["volume"], **clean_params)
            elif name.upper() in ["MA", "EMA", "BBI", "RSI", "BIAS", "DMA", "TRIX"]:
                return indicator.compute(data["close"], **clean_params)
            elif name.upper() in ["DMI", "WR", "CCI"]:
                return indicator.compute(
                    data["high"], data["low"], data["close"], **clean_params
                )
            elif name.upper() == "VR":
                return indicator.compute(data["close"], data["volume"], **clean_params)
            elif name.upper() == "PSY":
                return indicator.compute(data["close"], **clean_params)
            elif name.upper() == "ARBR":
                return indicator.compute(
                    data["open"],
                    data["high"],
                    data["low"],
                    data["close"],
                    **clean_params,
                )
            elif name.upper() == "MFI":
                return indicator.compute(
                    data["high"],
                    data["low"],
                    data["close"],
                    data["volume"],
                    **clean_params,
                )
            elif name.upper() == "WAD":
                return indicator.compute(
                    data["high"], data["low"], data["close"], data["volume"]
                )
            elif name.upper() == "CMF":
                return indicator.compute(
                    data["high"],
                    data["low"],
                    data["close"],
                    data["volume"],
                    **clean_params,
                )
            elif name.upper() == "STOCHRSI":
                return indicator.compute(data["close"], **clean_params)
            elif name.upper() == "DONCHIAN":
                return indicator.compute(data["high"], data["low"], **clean_params)
            elif name.upper() == "ULTIMATE":
                return indicator.compute(
                    data["high"], data["low"], data["close"], **clean_params
                )

        return indicator.compute(data, **clean_params)


def compute_indicators(ohlcv: Dict, indicators: List[str] = None) -> Dict:
    ti = TechnicalIndicators()

    if indicators is None:
        indicators = ti.list_indicators()

    close = np.array(ohlcv["close"])
    high = np.array(ohlcv.get("high", close))
    low = np.array(ohlcv.get("low", close))
    volume = np.array(ohlcv.get("volume", np.zeros(len(close))))

    data = {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
        "open": np.array(ohlcv.get("open", close)),
    }

    result = {}
    for name in indicators:
        try:
            result[name] = ti.compute(name, data)
        except Exception as e:
            print(f"Error computing {name}: {e}")

    return result


__all__ = [
    "Indicator",
    "IndicatorResult",
    "IndicatorRegistry",
    "TechnicalIndicators",
    "compute_indicators",
    "MA",
    "EMA",
    "BBI",
    "SAR",
    "MACD",
    "KDJ",
    "RSI",
    "StochRSI",
    "BollingerBands",
    "ATR",
    "KeltnerChannel",
    "DonchianChannel",
    "OBV",
    "VWAP",
    "MFI",
    "WilliamsAD",
    "CMF",
    "VR",
    "WR",
    "CCI",
    "BIAS",
    "CR",
    "ARBR",
    "PSY",
    "DMI",
    "UltimateOscillator",
    "DMA",
    "TRIX",
]
