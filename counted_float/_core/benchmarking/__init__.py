from .counted_float import BenchmarkCountedFloat, BenchmarkFloat, CountedFloatBenchmarkResults
from .flops import FlopsBenchmarkResults, FlopsBenchmarkSuite


def run_flops_benchmark(n_seconds_per_run_target: float = 0.1) -> FlopsBenchmarkResults:
    """Run the flops benchmark suite with default settings returns a FlopsBenchmarkResults object."""

    benchmark_results = FlopsBenchmarkSuite().run(n_seconds_per_run_target=n_seconds_per_run_target)

    print()

    return benchmark_results


def run_counted_float_benchmark(t_target_sec: float = 0.1) -> CountedFloatBenchmarkResults:
    """Run benchmark to compare performance of float vs CountedFloat."""
    print("-" * 120)
    print("Running CountedFloat benchmark...")
    print()

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
    print("-" * 120)
    print()

    return CountedFloatBenchmarkResults(
        float_time_nsec=result_float.summary_stats_nsecs_per_exec().q50,
        counted_float_time_nsec=result_counted_float.summary_stats_nsecs_per_exec().q50,
    )
