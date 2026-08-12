"""Evaluating the library itself, as opposed to benchmarking the machine it runs on."""

from .practical_workload import CountedFloatBisection, FloatBisection
from .results import CountingOverheadResults, ExcludedFlopType, PerFlopTypeOverhead
from .runner import evaluate_counting_overhead
