"""Tests for CountedFloat's numeric-protocol behavior with non-float operand types.

CountedFloat must delegate to the other operand exactly like plain float does (returning
NotImplemented so Python can try the reflected operation), must raise float's TypeError for
genuinely unsupported operands, and must count an operation only when the float layer actually
performed it.
"""

import operator
from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction

import pytest

from counted_float._core.counting._counted_float import CountedFloat
from counted_float._core.counting._global_counter import GlobalFlopCounter

ARITHMETIC_OPERATORS = [operator.add, operator.sub, operator.mul, operator.truediv, operator.pow]
COMPARISON_OPERATORS = [operator.eq, operator.ne, operator.lt, operator.le, operator.gt, operator.ge]


class ReflectedOps:
    """Minimal foreign type implementing only reflected operators, as a stand-in for third-party numerics."""

    def __radd__(self, other: float) -> str:
        return "radd"

    def __rsub__(self, other: float) -> str:
        return "rsub"

    def __rmul__(self, other: float) -> str:
        return "rmul"

    def __rtruediv__(self, other: float) -> str:
        return "rtruediv"

    def __rpow__(self, other: float) -> str:
        return "rpow"

    def __gt__(self, other: float) -> str:
        return "gt"  # reflected counterpart of CountedFloat.__lt__


# =================================================================================================
#  Delegation to the other operand
# =================================================================================================
@pytest.mark.parametrize("op", [operator.add, operator.sub, operator.mul, operator.truediv])
def test_arithmetic_with_fraction_matches_float(op: Callable, global_counter: GlobalFlopCounter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.5)
    frac = Fraction(1, 2)

    # --- act ---------------------------------------------
    result = op(cf, frac)

    # --- assert ------------------------------------------
    # value & type parity with plain float; the delegated operation is deliberately NOT counted
    # and the result demotes to plain float (documented known limitation)
    assert result == op(1.5, frac)
    assert type(result) is float
    assert global_counter.total_count() == 0


def test_pow_with_fraction_stays_counted(global_counter: GlobalFlopCounter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.5)

    # --- act ---------------------------------------------
    result = cf ** Fraction(1, 2)

    # --- assert ------------------------------------------
    # unlike the other operators, Fraction.__rpow__ computes base ** float(exponent) without
    # stripping the subclass, so the operation lands back in CountedFloat.__pow__: the result
    # stays contagious and is counted
    assert result == 1.5 ** Fraction(1, 2)
    assert isinstance(result, CountedFloat)
    assert global_counter.POW == 1


@pytest.mark.parametrize("op", COMPARISON_OPERATORS)
def test_comparison_with_fraction_matches_float(op: Callable, global_counter: GlobalFlopCounter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.5)
    frac = Fraction(1, 2)

    # --- act ---------------------------------------------
    result = op(cf, frac)

    # --- assert ------------------------------------------
    assert result == op(1.5, frac)
    assert global_counter.total_count() == 0


def test_reflected_operators_of_foreign_type_win(global_counter: GlobalFlopCounter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.5)
    foreign = ReflectedOps()

    # --- act & assert ------------------------------------
    assert cf + foreign == "radd"
    assert cf - foreign == "rsub"
    assert cf * foreign == "rmul"
    assert cf / foreign == "rtruediv"
    assert cf**foreign == "rpow"
    assert (cf < foreign) == "gt"
    assert global_counter.total_count() == 0


# =================================================================================================
#  Unsupported operands raise float's TypeError
# =================================================================================================
@pytest.mark.parametrize("op", ARITHMETIC_OPERATORS)
@pytest.mark.parametrize("other", ["abc", Decimal("0.5"), None])
def test_arithmetic_with_unsupported_operand_raises(
    op: Callable, other: object, global_counter: GlobalFlopCounter
):
    # --- act & assert ------------------------------------
    # error parity with plain float (the exact message varies: str.__rmul__ raises its own
    # "can't multiply sequence" TypeError, exactly as for plain float)
    with pytest.raises(TypeError):
        op(1.5, other)
    with pytest.raises(TypeError):
        op(CountedFloat(1.5), other)
    assert global_counter.total_count() == 0


def test_ordering_with_unsupported_operand_raises(global_counter: GlobalFlopCounter):
    # --- act & assert ------------------------------------
    with pytest.raises(TypeError):
        _ = CountedFloat(1.5) < "abc"
    assert global_counter.total_count() == 0


def test_equality_with_unsupported_operand_is_uncounted(global_counter: GlobalFlopCounter):
    # --- act ---------------------------------------------
    result = CountedFloat(1.5) == "abc"  # resolves via identity fallback, not a float comparison

    # --- assert ------------------------------------------
    assert result is False
    assert global_counter.total_count() == 0


# =================================================================================================
#  Failed operations do not count
# =================================================================================================
def test_failed_division_is_uncounted(global_counter: GlobalFlopCounter):
    # --- act ---------------------------------------------
    with pytest.raises(ZeroDivisionError):
        _ = CountedFloat(1.5) / CountedFloat(0.0)
    with pytest.raises(ZeroDivisionError):
        _ = 1.5 / CountedFloat(0.0)  # via __rtruediv__

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 0


def test_failed_pow_is_uncounted(global_counter: GlobalFlopCounter):
    # --- act ---------------------------------------------
    with pytest.raises(OverflowError):
        _ = CountedFloat(2.0) ** 1e6

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 0


def test_complex_pow_result_matches_float_and_is_uncounted(global_counter: GlobalFlopCounter):
    # --- act ---------------------------------------------
    result_pow = CountedFloat(-8.0) ** 0.333
    result_rpow = (-8.0) ** CountedFloat(0.333)

    # --- assert ------------------------------------------
    # a negative base with fractional exponent yields complex, exactly like plain float;
    # complex results fall outside the counting model
    assert result_pow == (-8.0) ** 0.333
    assert result_rpow == (-8.0) ** 0.333
    assert isinstance(result_pow, complex)
    assert isinstance(result_rpow, complex)
    assert global_counter.total_count() == 0
