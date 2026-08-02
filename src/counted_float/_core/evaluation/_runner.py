"""The counting-overhead entry point.

What this measures is the library, not the machine — how much slower arithmetic becomes when it is
counted. That is a meta-observation about counted-float rather than a peer of the flops benchmark
suite, which is why it lives here and not beside it.
"""

from counted_float._core.micro_benchmarking import console, output_quiet
from counted_float._core.models import FlopType

from ._per_flop_overhead import EXCLUDED_FLOP_TYPES, PER_FLOP_TYPE_SPECS, PerFlopTypeLoop
from ._practical_workload import PRACTICAL_WORKLOAD_LABEL, CountedFloatBisection, FloatBisection
from ._results import CountingOverheadResults, ExcludedFlopType, PerFlopTypeOverhead


def evaluate_counting_overhead(t_target_sec: float = 0.1, verbose: bool = True) -> CountingOverheadResults:
    """Compare the cost of plain float arithmetic with the same arithmetic counted.

    Measures every flop type with a standalone loop (each type's float/CountedFloat pair, per-type
    exclusions listed in the result), then the practical mixed workload. Progress output is
    printed unless verbose is False.

    Args:
        t_target_sec: Target wall time per timed run; the total evaluation runs a few hundred
            times this long (two variants of every measured type, plus the practical workload).
        verbose: Whether per-run progress is printed while measuring.
    """
    with output_quiet(not verbose):
        console.print("-" * 120, soft_wrap=True)
        console.print("Evaluating counting overhead...")
        console.print()

        # --- per-flop-type loops --------------------
        per_flop_type: list[PerFlopTypeOverhead] = []
        for spec in PER_FLOP_TYPE_SPECS:
            pool_float = spec.make_pool(False)
            pool_counted = spec.make_pool(True)
            result_float = PerFlopTypeLoop(
                name=f"{spec.flop_type.name} [float]",
                loop=spec.loop,
                pool=pool_float,
                in_counting_context=False,
            ).run_many(n_runs_total=20, n_runs_warmup=5, n_seconds_per_run_target=t_target_sec)
            result_counted = PerFlopTypeLoop(
                name=f"{spec.flop_type.name} [CountedFloat]",
                loop=spec.loop,
                pool=pool_counted,
                in_counting_context=True,
            ).run_many(n_runs_total=20, n_runs_warmup=5, n_seconds_per_run_target=t_target_sec)
            per_flop_type.append(
                PerFlopTypeOverhead(
                    flop_type=spec.flop_type,
                    expression=spec.expression,
                    float_time_nsec=result_float.summary_stats_nsecs_per_exec().q50 / len(pool_float),
                    counted_float_time_nsec=result_counted.summary_stats_nsecs_per_exec().q50 / len(pool_counted),
                )
            )

        # --- practical workload ---------------------
        result_float_bisection = FloatBisection().run_many(
            n_runs_total=50,
            n_runs_warmup=15,
            n_seconds_per_run_target=t_target_sec,
        )
        result_counted_bisection = CountedFloatBisection().run_many(
            n_runs_total=50,
            n_runs_warmup=15,
            n_seconds_per_run_target=t_target_sec,
        )

        console.print("-" * 120, soft_wrap=True)
        console.print()

    return CountingOverheadResults(
        per_flop_type=per_flop_type,
        excluded_flop_types=[
            ExcludedFlopType(flop_type=flop_type, reason=EXCLUDED_FLOP_TYPES[flop_type])
            for flop_type in FlopType
            if flop_type in EXCLUDED_FLOP_TYPES
        ],
        practical_workload_label=PRACTICAL_WORKLOAD_LABEL,
        float_time_nsec=result_float_bisection.summary_stats_nsecs_per_exec().q50,
        counted_float_time_nsec=result_counted_bisection.summary_stats_nsecs_per_exec().q50,
    )
