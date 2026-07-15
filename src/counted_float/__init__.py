"""Top-level public API for flop counting: CountedFloat, FlopCountingContext, and related models."""

from importlib.metadata import PackageNotFoundError, version
from types import ModuleType
from typing import TYPE_CHECKING

import counted_float.config as config

if TYPE_CHECKING:
    import counted_float.benchmarking as benchmarking

try:
    __version__ = version("counted-float")
except PackageNotFoundError:  # source tree without installed package metadata
    __version__ = "0.0.0"

from ._core.counting import BuiltInData, CountedFloat, FlopCountingContext, PauseFlopCounting
from ._core.models import FlopCounts, FlopType, FlopWeights, Quantiles, SystemInfo

__all__ = [
    "CountedFloat",
    "FlopCountingContext",
    "FlopCounts",
    "FlopType",
    "FlopWeights",
    "PauseFlopCounting",
    "Quantiles",
    "SystemInfo",
    "__version__",
    "benchmarking",
    "config",
]


def __getattr__(name: str) -> ModuleType:
    """Resolve the benchmarking subpackage on first access.

    Benchmarking pulls in numba and rich, which the counting core never touches. Importing it
    eagerly would make every importer -- including those who only count flops -- pay for the
    benchmarking toolchain, which is the bulk of this package's import cost.

    Args:
        name: Attribute being looked up on the package.

    Returns:
        The imported `counted_float.benchmarking` module.

    Raises:
        AttributeError: For any other attribute name.
    """
    if name == "benchmarking":
        import counted_float.benchmarking as benchmarking

        globals()["benchmarking"] = benchmarking  # resolve once; later lookups skip __getattr__
        return benchmarking
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
