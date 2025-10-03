from __future__ import annotations

import random
from abc import ABC, abstractmethod

import numpy as np


# =================================================================================================
#  Base class
# =================================================================================================
class ArrayGenerator(ABC):
    # -------------------------------------------------------------------------
    #  API
    # -------------------------------------------------------------------------
    @abstractmethod
    def new_array(self, size: int) -> np.ndarray:
        """Generates random 1D numpy array of requested size"""
        raise NotImplementedError

    # -------------------------------------------------------------------------
    #  Factory Methods
    # -------------------------------------------------------------------------
    @classmethod
    def lin_range(cls, min_value: float, max_value: float) -> ArrayGenerator:
        return ArrayGeneratorLinear(min_value, max_value)

    @classmethod
    def log_range(cls, min_value: float, max_value: float) -> ArrayGenerator:
        return ArrayGeneratorLog(min_value, max_value)


# =================================================================================================
#  Implementations
# =================================================================================================
class ArrayGeneratorLinear(ArrayGenerator):
    def __init__(self, min_value: float, max_value: float):
        """Array generator, where values are in interval [min_value, max_value] with avg. equal to mid-point."""
        self.min_value = min_value
        self.max_value = max_value

    def new_array(self, size: int) -> np.ndarray:
        uniform_values = 0.5 * (1.0 + _random_balanced_values(size))  # uniform random values in [0,1]
        return self.min_value + uniform_values * (self.max_value - self.min_value)


class ArrayGeneratorLog(ArrayGenerator):
    def __init__(self, min_value: float, max_value: float):
        """Array generator, where values are in interval [min_value, max_value] with geomean of values eq. to geo-mid"""
        self.min_value = min_value
        self.max_value = max_value

    def new_array(self, size: int) -> np.ndarray:
        uniform_values = 0.5 * (1.0 + _random_balanced_values(size))  # uniform random values in [0,1]
        return self.min_value * (self.max_value / self.min_value) ** uniform_values


# =================================================================================================
#  Helpers
# =================================================================================================
def _random_balanced_values(size: int) -> np.ndarray:
    """
    Returns random values in [-1,1], such that...
      - mean value == 0.0
      - cumulative sum of any arbitrary first n values also lies within [-1,1]
    """
    cumsum = 0.0
    lst = []
    for i in range(size - 1):
        next_min_value = max(-1.0, -1.0 - cumsum)
        next_max_value = min(1.0, 1.0 - cumsum)
        next_value = random.uniform(next_min_value, next_max_value)
        lst.append(next_value)
        cumsum += next_value
    lst.append(-cumsum)
    return np.array(lst)
