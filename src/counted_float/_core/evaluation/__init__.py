"""Evaluating the library itself, as opposed to benchmarking the machine it runs on."""

from ._overhead_evaluation import CountedFloatEvaluation, CountingOverheadResults, FloatEvaluation
from ._runner import evaluate_counting_overhead
