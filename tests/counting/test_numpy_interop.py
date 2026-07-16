"""Interop with numpy scalars, for the direction whose counting semantics are settled.

``np.float64`` subclasses ``float``, so with a ``CountedFloat`` on the left the operator is
handled here: the flop is counted and the result stays a ``CountedFloat``. These tests pin that
direction.

With a numpy scalar on the left, numpy handles the operation instead and nothing is counted.
That is a known gap rather than a contract, so it is deliberately not pinned here.
"""

import operator
from collections.abc import Callable

import numpy as np
import pytest

from counted_float import CountedFloat, FlopCountingContext


@pytest.mark.parametrize(
    ("op", "flop_type_name"),
    [
        (operator.add, "ADD"),
        (operator.sub, "SUB"),
        (operator.mul, "MUL"),
        (operator.truediv, "DIV"),
    ],
)
def test_counted_float_on_the_left_of_a_numpy_scalar_counts_and_stays_counted(
    op: Callable[[object, object], object], flop_type_name: str
):
    # --- arrange -----------------------------------------
    counted = CountedFloat(6.0)
    numpy_scalar = np.float64(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        result = op(counted, numpy_scalar)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert getattr(fcc.flop_counts(), flop_type_name) == 1
    assert fcc.flop_counts().total_count() == 1


def test_counted_float_compared_against_a_numpy_scalar_counts():
    # --- arrange -----------------------------------------
    counted = CountedFloat(1.0)
    numpy_scalar = np.float64(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        result = counted < numpy_scalar

    # --- assert ------------------------------------------
    assert result is True
    assert fcc.flop_counts().COMP == 1


def test_counted_float_on_the_left_of_a_numpy_scalar_keeps_the_value_right():
    # --- arrange -----------------------------------------
    counted = CountedFloat(6.0)
    numpy_scalar = np.float64(3.0)

    # --- act ---------------------------------------------
    quotient = counted / numpy_scalar

    # --- assert ------------------------------------------
    assert quotient == 2.0
