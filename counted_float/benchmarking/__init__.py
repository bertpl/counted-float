"""Public benchmarking API: run flop and CountedFloat benchmarks and inspect their results."""

from counted_float._core.benchmarking import FlopsBenchmarkResults, run_counted_float_benchmark, run_flops_benchmark

__all__ = [
    "FlopsBenchmarkResults",
    "run_counted_float_benchmark",
    "run_flops_benchmark",
]
