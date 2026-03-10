from typing import Dict
from dataclasses import dataclass
import numpy as np


@dataclass
class IndicatorResult:
    name: str
    value: float
    signal: str = ""
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Indicator:
    name: str = ""
    params: Dict = {}

    def compute(self, data: np.ndarray, **kwargs) -> np.ndarray:
        raise NotImplementedError

    def __call__(self, data: np.ndarray, **kwargs) -> np.ndarray:
        return self.compute(data, **kwargs)
