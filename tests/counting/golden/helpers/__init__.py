"""Machinery the golden tests run on: probe execution, outcome comparison, and the assertions."""

from .coverage import patched_math_names, reachable_dunders, record_corpus_coverage
from .docs_anchors import interpretation_slugs, rules_anchors
from .runner import (
    REGIMES,
    ProbeRun,
    assert_result_shape,
    comparable_outcome,
    gate_reason,
    raw_result,
    run_probe,
    scaled_counts,
)

__all__ = [
    "REGIMES",
    "ProbeRun",
    "assert_result_shape",
    "comparable_outcome",
    "gate_reason",
    "interpretation_slugs",
    "patched_math_names",
    "raw_result",
    "reachable_dunders",
    "record_corpus_coverage",
    "rules_anchors",
    "run_probe",
    "scaled_counts",
]
