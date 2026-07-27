"""Benchmarking facade, with the flops suite reached lazily.

The flops suite is the only part of this package that needs the benchmarking extra, so it resolves
on first use rather than on import — which keeps the overhead benchmark next door, and everything
that merely reads a stored result, working on an install without that extra. FlopsBenchmarkResults
is a plain model rather than part of the suite, so it comes straight from its own package and stays
eagerly available.

The hook below is the only way into the flops sub-package; the entry points live in `_runners` so
that they reach it the same way any outside caller does.
"""

from typing import TYPE_CHECKING

from counted_float._core.compatibility import Capability
from counted_float._core.models import FlopsBenchmarkResults

from ._output import console, output_quiet
from ._runners import run_counted_float_benchmark, run_flops_benchmark
from .counted_float import BenchmarkCountedFloat, BenchmarkFloat, CountedFloatBenchmarkResults

if TYPE_CHECKING:
    from .flops import FlopsBenchmarkSuite


def __getattr__(name: str) -> object:
    """Resolve the flops suite on first access, reporting a missing extra as install guidance."""
    if name != "FlopsBenchmarkSuite":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    with Capability.FLOPS_BENCHMARKING.required():
        from . import flops

    return flops.FlopsBenchmarkSuite
