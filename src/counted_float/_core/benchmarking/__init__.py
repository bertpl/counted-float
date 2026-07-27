"""Benchmarking entry points, with the flops suite reached lazily.

The flops suite is the only part of this package that needs the benchmarking extra, so it is
imported on use rather than on import — that keeps the overhead benchmark next door, and everything
that merely reads a stored result, working on an install that does not carry those modules.
FlopsBenchmarkResults is a plain model rather than part of the suite, so it comes straight from
its own package and stays eagerly available.
"""

from types import ModuleType
from typing import TYPE_CHECKING

from counted_float._core.compatibility import FLOPS_BENCHMARKING
from counted_float._core.models import FlopsBenchmarkResults

from ._output import console, output_quiet
from .counted_float import BenchmarkCountedFloat, BenchmarkFloat, CountedFloatBenchmarkResults

if TYPE_CHECKING:
    from .flops import FlopsBenchmarkSuite

_LAZY_FLOPS_EXPORTS = ("FlopsBenchmarkSuite",)


def __getattr__(name: str) -> object:
    """Resolve a flops export on first attribute access from outside this module."""
    if name in _LAZY_FLOPS_EXPORTS:
        return getattr(import_flops(), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def import_flops() -> ModuleType:
    """Import the flops sub-package, translating its missing dependencies into install guidance.

    The hook above only fires for attribute access from *outside* this module, so callers within it
    go through this function instead of naming the export directly.
    """
    try:
        from . import flops
    except ModuleNotFoundError as e:
        if FLOPS_BENCHMARKING.explains(e):
            raise ModuleNotFoundError(FLOPS_BENCHMARKING.missing_dependency_message(), name=e.name) from None
        raise
    return flops


def run_flops_benchmark(
    t_slice_target_ms: float = 20.0,
    n_rounds_measure: int = 200,
    n_rounds_warmup: int = 3,
    seed: int | None = None,
    verbose: bool = True,
) -> FlopsBenchmarkResults:
    """Run the flops benchmark suite (round-robin interleaved) and return a FlopsBenchmarkResults object.

    An optional seed makes input pools and per-round shuffles reproducible. Progress output is
    printed unless verbose is False; a missing-numba RuntimeWarning is emitted regardless.
    """
    flops_benchmark_suite: type[FlopsBenchmarkSuite] = import_flops().FlopsBenchmarkSuite

    with output_quiet(not verbose):
        benchmark_results = flops_benchmark_suite().run(
            t_slice_target_ms=t_slice_target_ms,
            n_rounds_measure=n_rounds_measure,
            n_rounds_warmup=n_rounds_warmup,
            seed=seed,
        )
        console.print()

    return benchmark_results


def run_counted_float_benchmark(t_target_sec: float = 0.1, verbose: bool = True) -> CountedFloatBenchmarkResults:
    """Run benchmark to compare performance of float vs CountedFloat.

    Progress output is printed unless verbose is False.
    """
    with output_quiet(not verbose):
        console.print("-" * 120, soft_wrap=True)
        console.print("Running CountedFloat benchmark...")
        console.print()

        result_float = BenchmarkFloat().run_many(
            n_runs_total=50,
            n_runs_warmup=15,
            n_seconds_per_run_target=t_target_sec,
        )
        result_counted_float = BenchmarkCountedFloat().run_many(
            n_runs_total=50,
            n_runs_warmup=15,
            n_seconds_per_run_target=t_target_sec,
        )

        console.print("-" * 120, soft_wrap=True)
        console.print()

    return CountedFloatBenchmarkResults(
        float_time_nsec=result_float.summary_stats_nsecs_per_exec().q50,
        counted_float_time_nsec=result_counted_float.summary_stats_nsecs_per_exec().q50,
    )
