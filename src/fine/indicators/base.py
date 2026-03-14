from abc import abstractmethod, ABC
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


class Indicator(ABC):
    name: str = ""
    params: Dict = {}

    @abstractmethod
    def compute(self, **kwargs) -> np.ndarray:
        pass

    def __call__(self, **kwargs) -> np.ndarray:
        return self.compute(**kwargs)
