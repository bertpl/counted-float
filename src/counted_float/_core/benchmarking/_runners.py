"""The two benchmark entry points.

These live beside the package facade rather than inside it on purpose. A module-level ``__getattr__``
only fires for attribute access from *outside* the module that defines it, so a runner sitting in
``__init__`` could not reach the flops suite through the same hook every other caller uses — it
would need a second way in, and a second way in is a second thing that can miss the guard.
"""

from counted_float._core.models import FlopsBenchmarkResults

from ._output import console, output_quiet
from .counted_float import BenchmarkCountedFloat, BenchmarkFloat, CountedFloatBenchmarkResults


def run_flops_benchmark(
    t_slice_target_ms: float = 20.0,
    n_rounds_measure: int = 200,
    n_rounds_warmup: int = 3,
    seed: int | None = None,
    verbose: bool = True,
) -> FlopsBenchmarkResults:
    """Run the flops benchmark suite (round-robin interleaved) and return a FlopsBenchmarkResults object.

    An optional seed makes input pools and per-round shuffles reproducible. Progress output is
    printed unless verbose is False.
    """
    # deliberately through the package rather than `from .flops import ...`: that is what puts this
    # call through the guarded hook, so it reports the missing extra instead of a raw import error
    from counted_float._core.benchmarking import FlopsBenchmarkSuite

    with output_quiet(not verbose):
        benchmark_results = FlopsBenchmarkSuite().run(
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
