from ._core.counting import CountedFloat, FlopCountingContext, PauseFlopCounting
from ._core.counting.models import (
    FlopCounts,
    FlopsBenchmarkDurations,
    FlopsBenchmarkResults,
    FlopType,
    FlopWeights,
    FPUInstruction,
    SystemInfo,
)

__all__ = [
    "CountedFloat",
    "FlopCountingContext",
    "FlopCounts",
    "FlopsBenchmarkDurations",
    "FlopsBenchmarkResults",
    "FlopType",
    "FlopWeights",
    "FPUInstruction",
    "PauseFlopCounting",
    "SystemInfo",
]

# -------------------------------------------------------------------------
#  Optional [benchmarking] dependencies
# -------------------------------------------------------------------------
from ._core._optional_deps import FLAG_BENCHMARK_DEPS

if FLAG_BENCHMARK_DEPS:
    import counted_float.benchmarking as benchmarking

    __all__.append("benchmarking")

# delete variable again, we don't want to expose this
del FLAG_BENCHMARK_DEPS
