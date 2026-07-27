"""The counting-overhead entry point.

What this measures is the library, not the machine — how much slower arithmetic becomes when it is
counted. That is a meta-observation about counted-float rather than a peer of the flops benchmark
suite, which is why it lives here and not beside it.
"""

from counted_float._core.micro import console, output_quiet

from ._counted_float_benchmark import BenchmarkCountedFloat, BenchmarkFloat, CountedFloatBenchmarkResults


def evaluate_counting_overhead(t_target_sec: float = 0.1, verbose: bool = True) -> CountedFloatBenchmarkResults:
    """Compare the cost of plain float arithmetic with the same arithmetic counted.

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
