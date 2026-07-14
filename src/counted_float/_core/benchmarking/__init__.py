from .counted_float import BenchmarkCountedFloat, BenchmarkFloat, CountedFloatBenchmarkResults
from .flops import FlopsBenchmarkResults, FlopsBenchmarkSuite


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
    benchmark_results = FlopsBenchmarkSuite().run(
        t_slice_target_ms=t_slice_target_ms,
        n_rounds_measure=n_rounds_measure,
        n_rounds_warmup=n_rounds_warmup,
        seed=seed,
        verbose=verbose,
    )

    if verbose:
        print()

    return benchmark_results


def run_counted_float_benchmark(t_target_sec: float = 0.1, verbose: bool = True) -> CountedFloatBenchmarkResults:
    """Run benchmark to compare performance of float vs CountedFloat.

    Progress output is printed unless verbose is False.
    """
    if verbose:
        print("-" * 120)
        print("Running CountedFloat benchmark...")
        print()

    result_float = BenchmarkFloat().run_many(
        n_runs_total=50,
        n_runs_warmup=15,
        n_seconds_per_run_target=t_target_sec,
        verbose=verbose,
    )
    result_counted_float = BenchmarkCountedFloat().run_many(
        n_runs_total=50,
        n_runs_warmup=15,
        n_seconds_per_run_target=t_target_sec,
        verbose=verbose,
    )
    if verbose:
        print("-" * 120)
        print()

    return CountedFloatBenchmarkResults(
        float_time_nsec=result_float.summary_stats_nsecs_per_exec().q50,
        counted_float_time_nsec=result_counted_float.summary_stats_nsecs_per_exec().q50,
    )
