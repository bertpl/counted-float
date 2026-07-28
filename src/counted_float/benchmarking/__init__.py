"""Public benchmarking API: run the flop benchmark suite and inspect its results.

``run_counted_float_benchmark`` still resolves here and is deprecated: what it measures is the
library rather than the machine, so it now lives in :mod:`counted_float.evaluation` as
``evaluate_counting_overhead``.
"""

import warnings

from counted_float._core.benchmarking import FlopsBenchmarkResults, run_flops_benchmark

__all__ = [
    "FlopsBenchmarkResults",
    "run_counted_float_benchmark",
    "run_flops_benchmark",
]


def __getattr__(name: str) -> object:
    """Serve `run_counted_float_benchmark`, warning once, from the surface a user actually imports."""
    if name == "run_counted_float_benchmark":
        from counted_float.evaluation import evaluate_counting_overhead

        warnings.warn(
            "run_counted_float_benchmark has moved to counted_float.evaluation as "
            "evaluate_counting_overhead; this alias will be removed in the next major version.",
            DeprecationWarning,
            stacklevel=2,
        )
        # bind it here so the warning fires once per process: `from x import y` consults __getattr__
        # twice -- once for the import machinery's own hasattr probe, once for the actual lookup
        globals()[name] = evaluate_counting_overhead
        return evaluate_counting_overhead
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
