"""Machinery the golden tests run on: probe execution, outcome comparison, and the assertions."""

from ._runner import (
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
    "raw_result",
    "run_probe",
    "scaled_counts",
]
