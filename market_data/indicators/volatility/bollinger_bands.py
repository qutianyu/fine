from typing import Dict
import numpy as np
from ..base import Indicator
from ..trend import EMA


class BollingerBands(Indicator):
    name = "BOLL"

    def compute(
        self, data: np.ndarray, period: int = 20, std_dev: float = 2.0
    ) -> Dict[str, np.ndarray]:
        if not isinstance(period, int):
            period = 20
        ma = EMA().compute(data, period)
        std = np.zeros(len(data))

        for i in range(period - 1, len(data)):
            std[i] = np.std(data[i - period + 1 : i + 1])

        upper = ma + std_dev * std
        lower = ma - std_dev * std

        return {
            "upper": upper,
            "middle": ma,
            "lower": lower,
            "bandwidth": (upper - lower) / ma,
            "percent": (data - lower) / (upper - lower + 1e-10),
        }
