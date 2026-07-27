"""Evaluating the library itself, as opposed to benchmarking the machine it runs on."""

from ._counted_float_benchmark import BenchmarkCountedFloat, BenchmarkFloat, CountedFloatBenchmarkResults
from ._runner import evaluate_counting_overhead
