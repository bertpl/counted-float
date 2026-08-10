"""Machinery the golden tests run on: probe execution, outcome comparison, and the assertions."""

from .coverage import patched_math_names, reachable_dunders, record_corpus_coverage
from .docs_anchors import interpretation_slugs, rules_anchors
from .runner import REGIMES, assert_result_shape, gate_reason, run_probe

__all__ = [
    "REGIMES",
    "assert_result_shape",
    "gate_reason",
    "interpretation_slugs",
    "patched_math_names",
    "reachable_dunders",
    "record_corpus_coverage",
    "rules_anchors",
    "run_probe",
]
