"""The flops benchmark entry point.

It lives beside the package facade rather than inside it on purpose. A module-level ``__getattr__``
only fires for attribute access from *outside* the module that defines it, so a runner sitting in
``__init__`` could not reach the flops suite through the same hook every other caller uses — it
would need a second way in, and a second way in is a second thing that can miss the guard.
"""

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
