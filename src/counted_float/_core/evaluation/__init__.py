"""Evaluating the library itself, as opposed to benchmarking the machine it runs on."""

from ._practical_workload import CountedFloatBisection, FloatBisection
from ._results import CountingOverheadResults, ExcludedFlopType, PerFlopTypeOverhead
from ._runner import evaluate_counting_overhead
