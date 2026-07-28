"""The counting-overhead entry point.

What this measures is the library, not the machine — how much slower arithmetic becomes when it is
counted. That is a meta-observation about counted-float rather than a peer of the flops benchmark
suite, which is why it lives here and not beside it.
"""

from counted_float._core.micro_benchmarking import console, output_quiet

from ._overhead_evaluation import CountedFloatEvaluation, CountingOverheadResults, FloatEvaluation


def evaluate_counting_overhead(t_target_sec: float = 0.1, verbose: bool = True) -> CountingOverheadResults:
    """Compare the cost of plain float arithmetic with the same arithmetic counted.

    Progress output is printed unless verbose is False.
    """
    with output_quiet(not verbose):
        console.print("-" * 120, soft_wrap=True)
        console.print("Evaluating counting overhead...")
        console.print()

        result_float = FloatEvaluation().run_many(
            n_runs_total=50,
            n_runs_warmup=15,
            n_seconds_per_run_target=t_target_sec,
        )
        result_counted_float = CountedFloatEvaluation().run_many(
            n_runs_total=50,
            n_runs_warmup=15,
            n_seconds_per_run_target=t_target_sec,
        )

        console.print("-" * 120, soft_wrap=True)
        console.print()

    return CountingOverheadResults(
        float_time_nsec=result_float.summary_stats_nsecs_per_exec().q50,
        counted_float_time_nsec=result_counted_float.summary_stats_nsecs_per_exec().q50,
    )
