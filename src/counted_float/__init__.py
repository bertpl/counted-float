"""Top-level public API for flop counting: CountedFloat, FlopCountingContext, and related models."""

from importlib.metadata import PackageNotFoundError, version

import counted_float.config as config

try:
    __version__ = version("counted-float")
except PackageNotFoundError:  # source tree without installed package metadata
    __version__ = "0.0.0"

from ._core.counting import BuiltInData, CountedFloat, FlopCountingContext, PauseFlopCounting
from ._core.models import FlopCounts, FlopType, FlopWeights, Quantiles, SystemInfo

__all__ = [
    "BuiltInData",
    "CountedFloat",
    "FlopCountingContext",
    "FlopCounts",
    "FlopType",
    "FlopWeights",
    "PauseFlopCounting",
    "Quantiles",
    "SystemInfo",
    "__version__",
    "config",
]
