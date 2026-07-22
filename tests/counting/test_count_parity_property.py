"""Property-based test: an operation counts the same regardless of which side the counted value
sits on.

This is the property whose absence let the numpy scalar under-count survive: with a numpy scalar
on the left, the flops silently vanished while the result type recovered downstream. It is
asserted over the operand types the counting model deliberately supports — ``float``, ``int``,
and ``np.float64`` (a plain C double flowing through the ordinary float path). ``Fraction`` is
deliberately absent: its asymmetry is a documented boundary of the model, not a target.

One asymmetry is the model's own: division's reciprocal fold keys on the *divisor* being a
power-of-two constant, so ``cf / 2.0`` counts MUL while ``2.0 / cf`` (dynamic divisor) counts
DIV — and ``cf / 1.0`` folds away entirely. The parity test asserts exactly those splits for
such operands instead of blind equality.
"""

import operator
from collections.abc import Callable
from math import frexp

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from counted_float import CountedFloat, FlopCountingContext, FlopCounts

# --- strategies ----------------------------------------------------------------------------------
_nonzero_finite = st.floats(allow_nan=False, allow_infinity=False, width=64).filter(lambda v: v != 0.0)

_ARITHMETIC = [operator.add, operator.sub, operator.mul, operator.truediv]
_OPERAND_CONVERTERS: list[tuple[str, Callable[[float], object]]] = [
    ("float", float),
    ("int", lambda v: int(v) or 1),  # keep nonzero so division stays legal
    ("np.float64", np.float64),
]


def _counts_of(op: Callable, left: object, right: object) -> FlopCounts:
    """Flop counts of a single ``op(left, right)`` evaluation."""
    with FlopCountingContext() as fcc:
        op(left, right)
    return fcc.flop_counts()


def _is_foldable_power_of_two(value: float) -> bool:
    """Whether a constant divisor of this value takes the reciprocal-multiply fold (counts MUL)."""
    mantissa, exponent = frexp(value)
    return mantissa in (0.5, -0.5) and exponent >= -1022


@pytest.mark.parametrize("op", _ARITHMETIC)
@pytest.mark.parametrize(("operand_type", "convert"), _OPERAND_CONVERTERS, ids=[t[0] for t in _OPERAND_CONVERTERS])
@settings(deadline=None)
@given(x=_nonzero_finite, y=_nonzero_finite)
def test_operand_side_does_not_change_the_count(
    op: Callable, operand_type: str, convert: Callable[[float], object], x: float, y: float
) -> None:
    # --- arrange -----------------------------------------
    counted = CountedFloat(x)
    other = convert(y)

    # --- act ---------------------------------------------
    counts_counted_left = _counts_of(op, counted, other)
    counts_counted_right = _counts_of(op, other, counted)

    # --- assert ------------------------------------------
    if op is operator.truediv and float(other) == 1.0:
        # a constant divisor of 1 folds away entirely; as a dividend the division is real
        assert counts_counted_left.total_count() == 0
        assert counts_counted_right.DIV == 1
        assert counts_counted_right.total_count() == 1
        return
    if op is operator.truediv and _is_foldable_power_of_two(float(other)):
        # the model's own side-dependence (see module docstring): constant power-of-two
        # divisor folds to MUL, while as a dividend the divisor is dynamic and counts DIV
        assert counts_counted_left.MUL == 1
        assert counts_counted_right.DIV == 1
    else:
        assert counts_counted_left == counts_counted_right, (
            f"{op.__name__} with a {operand_type} operand counts differently per side"
        )
    assert counts_counted_left.total_count() == 1
    assert counts_counted_right.total_count() == 1


@pytest.mark.parametrize("op", _ARITHMETIC)
@pytest.mark.parametrize(("operand_type", "convert"), _OPERAND_CONVERTERS, ids=[t[0] for t in _OPERAND_CONVERTERS])
@settings(deadline=None)
@given(x=_nonzero_finite, y=_nonzero_finite)
def test_operand_side_does_not_change_the_result_type(
    op: Callable, operand_type: str, convert: Callable[[float], object], x: float, y: float
) -> None:
    # --- arrange -----------------------------------------
    counted = CountedFloat(x)
    other = convert(y)

    # --- act / assert ------------------------------------
    assert isinstance(op(counted, other), CountedFloat)
    assert isinstance(op(other, counted), CountedFloat)
