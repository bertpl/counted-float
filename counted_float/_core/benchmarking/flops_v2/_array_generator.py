from __future__ import annotations

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
        return self.min_value + _random_balanced_values(size) * (self.max_value - self.min_value)


class ArrayGeneratorLog(ArrayGenerator):
    def __init__(self, min_value: float, max_value: float):
        """Array generator, where values are in interval [min_value, max_value] with geomean of values eq. to geo-mid"""
        self.min_value = min_value
        self.max_value = max_value

    def new_array(self, size: int) -> np.ndarray:
        return self.min_value * (self.max_value / self.min_value) ** _random_balanced_values(size)


# =================================================================================================
#  Helpers
# =================================================================================================
def _random_balanced_values(size: int) -> np.ndarray:
    """Returns random values in (0,1), with avg=0.5"""
    v = np.linspace(0.5 / size, 1 - (0.5 / size), size)
    np.random.shuffle(v)
    return v
