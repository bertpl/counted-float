"""Property-based tests: a CountedFloat behaves exactly like the float it wraps.

For every supported operator and operand type, ``CountedFloat(x) op y`` must match ``x op y`` in
value, result type (contagion), and error behavior. These blanket the numeric contract that the
hand-written tests probe point-by-point: a point-by-point suite only reaches the operand types and
values someone thought to enumerate, so a hole in the protocol surface — a reflected operator, an
operand type that silently demotes to plain float — survives until a caller finds it. Only
operators are covered here; the patched ``math.*`` functions have their own tests in
``test_math_patching.py``.
"""

import math
import operator
from collections.abc import Callable
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from counted_float import CountedFloat

# --- strategies ----------------------------------------------------------------------------------
_floats = st.floats(allow_nan=True, allow_infinity=True, width=64)
_finite = st.floats(allow_nan=False, allow_infinity=False, width=64)

# operators whose result is a (contagious) float
_ARITHMETIC = [operator.add, operator.sub, operator.mul, operator.truediv, operator.floordiv, operator.mod]
_COMPARISONS = [operator.eq, operator.ne, operator.lt, operator.le, operator.gt, operator.ge]


# --- helpers -------------------------------------------------------------------------------------
def _outcome(op: Callable, a: object, b: object) -> tuple[str, object]:
    """Return ``("ok", value)`` or ``("err", ExceptionType)`` for ``op(a, b)``."""
    try:
        return ("ok", op(a, b))
    except Exception as e:  # noqa: BLE001 -- deliberately capturing to compare error parity with plain float
        return ("err", type(e))


def _values_match(plain: object, counted: object) -> bool:
    """Value parity, treating NaN as equal to NaN and allowing complex / tuple (divmod) results."""
    if isinstance(plain, tuple) and isinstance(counted, tuple):
        return len(plain) == len(counted) and all(_values_match(p, c) for p, c in zip(plain, counted, strict=True))
    if isinstance(plain, complex) or isinstance(counted, complex):
        return plain == counted
    p, c = float(plain), float(counted)  # ty: ignore[invalid-argument-type] -- both are real numbers here
    return (math.isnan(p) and math.isnan(c)) or p == c


def _assert_parity(op: Callable, x: float, other: object) -> None:
    """``op(CountedFloat(x), other)`` matches ``op(x, other)`` in value, type, and error."""
    plain = _outcome(op, x, other)
    counted = _outcome(op, CountedFloat(x), other)
    assert plain[0] == counted[0]  # both produced a value, or both raised
    if plain[0] == "err":
        assert plain[1] == counted[1]  # same exception type
    else:
        assert _values_match(plain[1], counted[1])


# --- arithmetic ----------------------------------------------------------------------------------
@pytest.mark.parametrize("op", _ARITHMETIC)
@settings(deadline=None)
@given(x=_floats, y=_floats)
def test_arithmetic_matches_float(op: Callable, x: float, y: float) -> None:
    _assert_parity(op, x, y)
    _assert_parity(op, x, CountedFloat(y))  # both operands counted


@pytest.mark.parametrize("op", _ARITHMETIC)
@settings(deadline=None)
@given(x=_finite, y=_finite)
def test_arithmetic_result_is_contagious(op: Callable, x: float, y: float) -> None:
    # whenever a real value is produced, it stays a CountedFloat
    kind, value = _outcome(op, CountedFloat(x), y)
    if kind == "ok":
        assert isinstance(value, CountedFloat)


@settings(deadline=None)
@given(x=_finite, y=_finite)
def test_pow_matches_float(x: float, y: float) -> None:
    # pow may produce a complex result for a negative base with a fractional exponent
    _assert_parity(operator.pow, x, y)


@settings(deadline=None)
@given(x=_floats, y=_floats)
def test_divmod_matches_float(x: float, y: float) -> None:
    _assert_parity(divmod, x, y)
    # when it produces a result, both quotient and remainder are contagious
    try:
        quotient, remainder = divmod(CountedFloat(x), y)
    except ZeroDivisionError:
        return
    assert isinstance(quotient, CountedFloat)
    assert isinstance(remainder, CountedFloat)


# --- comparisons ---------------------------------------------------------------------------------
@pytest.mark.parametrize("op", _COMPARISONS)
@settings(deadline=None)
@given(x=_floats, y=_floats)
def test_comparison_matches_float(op: Callable, x: float, y: float) -> None:
    result = op(CountedFloat(x), y)
    assert result == op(x, y)
    assert isinstance(result, bool)


# --- unary ---------------------------------------------------------------------------------------
@settings(deadline=None)
@given(x=_floats)
def test_unary_operators_match_float(x: float) -> None:
    for plain, counted in [(-x, -CountedFloat(x)), (+x, +CountedFloat(x)), (abs(x), abs(CountedFloat(x)))]:
        assert _values_match(plain, counted)
        assert isinstance(counted, CountedFloat)


# --- foreign / mixed operand types ---------------------------------------------------------------
@pytest.mark.parametrize("op", [*_ARITHMETIC, operator.pow])
@settings(deadline=None)
@given(x=_finite, n=st.integers(min_value=-1000, max_value=1000))
def test_arithmetic_with_int_operand_matches_float(op: Callable, x: float, n: int) -> None:
    _assert_parity(op, x, n)


@pytest.mark.parametrize("op", _ARITHMETIC)
@settings(deadline=None)
@given(x=_finite, frac=st.fractions())
def test_arithmetic_with_fraction_operand_matches_float(op: Callable, x: float, frac: Fraction) -> None:
    _assert_parity(op, x, frac)
