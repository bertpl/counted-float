"""The flops benchmark entry point: the one place the suite is reached from."""

from counted_float._core.compatibility import Capability
from counted_float._core.micro_benchmarking import console, output_quiet
from counted_float._core.models import FlopsBenchmarkResults


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
    # imported here, behind the guard, so that importing this module costs nothing and an install
    # without the extra is told what to install rather than shown a raw import error
    with Capability.FLOPS_BENCHMARKING.required():
        from .flops import FlopsBenchmarkSuite

    with output_quiet(not verbose):
        benchmark_results = FlopsBenchmarkSuite().run(
            t_slice_target_ms=t_slice_target_ms,
            n_rounds_measure=n_rounds_measure,
            n_rounds_warmup=n_rounds_warmup,
            seed=seed,
        )
        console.print()

    return benchmark_results
