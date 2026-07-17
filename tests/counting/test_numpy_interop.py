"""Interop with numpy: scalar doubles count from either side; everything else refuses loudly.

numpy counting is an explicit non-goal. CountedFloat refuses numpy's ufunc protocol
(``__array_ufunc__ = None``), so numpy's operators return NotImplemented and Python falls back to
CountedFloat's reflected methods: ``np.float64`` — a plain C double subclassing ``float`` — counts
correctly regardless of which side it sits on. ndarrays and numpy scalar dtypes that do not
subclass ``float`` raise ``TypeError`` instead of silently producing uncounted results.
"""

import operator
from collections.abc import Callable

import numpy as np
import pytest

from counted_float import CountedFloat, FlopCountingContext

_ARITHMETIC_OPS = [
    (operator.add, "ADD"),
    (operator.sub, "SUB"),
    (operator.mul, "MUL"),
    (operator.truediv, "DIV"),
]


# =================================================================================================
#  np.float64 scalars: counted from either side
# =================================================================================================
@pytest.mark.parametrize(("op", "flop_type_name"), _ARITHMETIC_OPS)
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


@pytest.mark.parametrize(("op", "flop_type_name"), _ARITHMETIC_OPS)
def test_counted_float_on_the_right_of_a_numpy_scalar_counts_and_stays_counted(
    op: Callable[[object, object], object], flop_type_name: str
):
    # --- arrange -----------------------------------------
    counted = CountedFloat(6.0)
    numpy_scalar = np.float64(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        result = op(numpy_scalar, counted)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert getattr(fcc.flop_counts(), flop_type_name) == 1
    assert fcc.flop_counts().total_count() == 1


def test_weighted_sum_with_numpy_weights_counts_every_flop():
    """The motivating defect: numpy weights on the left used to swallow every multiply while the
    running total recovered the CountedFloat type, so the loss was invisible."""
    # --- arrange -----------------------------------------
    weights = [np.float64(0.5), np.float64(0.25)]
    values = [CountedFloat(1.0), CountedFloat(2.0)]

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        total = CountedFloat(0.0)
        for weight, value in zip(weights, values, strict=True):
            total = total + weight * value

    # --- assert ------------------------------------------
    assert isinstance(total, CountedFloat)
    assert fcc.flop_counts().MUL == 2
    assert fcc.flop_counts().ADD == 2


@pytest.mark.parametrize("order", ["counted_left", "counted_right"])
def test_counted_float_compared_against_a_numpy_scalar_counts(order: str):
    # --- arrange -----------------------------------------
    counted = CountedFloat(1.0)
    numpy_scalar = np.float64(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        result = counted < numpy_scalar if order == "counted_left" else numpy_scalar > counted

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


# =================================================================================================
#  Everything else numpy: a loud boundary
# =================================================================================================
@pytest.mark.parametrize(("op", "flop_type_name"), _ARITHMETIC_OPS)
@pytest.mark.parametrize("counted_side", ["left", "right"])
def test_mixing_with_a_numpy_array_raises(
    op: Callable[[object, object], object], flop_type_name: str, counted_side: str
):
    # --- arrange -----------------------------------------
    counted = CountedFloat(2.0)
    array = np.array([1.0, 2.0])

    # --- act / assert ------------------------------------
    with pytest.raises(TypeError):
        op(counted, array) if counted_side == "left" else op(array, counted)


@pytest.mark.parametrize("scalar_type", [np.float32, np.int64], ids=["float32", "int64"])
def test_mixing_with_a_non_double_numpy_scalar_raises(scalar_type: type):
    """Only np.float64 subclasses float; other numpy scalar dtypes hit the same loud boundary."""
    # --- arrange -----------------------------------------
    counted = CountedFloat(2.0)
    scalar = scalar_type(3)

    # --- act / assert ------------------------------------
    with pytest.raises(TypeError):
        counted * scalar
    with pytest.raises(TypeError):
        scalar * counted
