"""Public evaluation API: measure what counting costs, on this machine, for this workload."""

from counted_float._core.evaluation import CountedFloatBenchmarkResults, evaluate_counting_overhead

__all__ = [
    "CountedFloatBenchmarkResults",
    "evaluate_counting_overhead",
]
