import math
import operator
import weakref
from collections.abc import Callable

import pytest

from counted_float._core.counting._counted_float import CountedFloat


# =================================================================================================
#  CountedFloat - Construction & other basics
# =================================================================================================
def test_counted_float_construction_and_equality():
    # --- arrange -----------------------------------------
    f = 7.0

    # --- act ---------------------------------------------
    cf = CountedFloat(f)
    ff = float(cf)

    # --- assert ------------------------------------------

    # check properties of cf
    assert cf == f
    assert isinstance(cf, float)
    assert isinstance(cf, CountedFloat)

    # check properties of ff
    assert ff == f
    assert isinstance(ff, float)
    assert not isinstance(ff, CountedFloat)


@pytest.mark.parametrize("f", [-1.0, 0.0, math.pi, math.e])
def test_counted_float_hash(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_hash = hash(f)
    cf_hash = hash(cf)

    # --- assert ------------------------------------------
    assert f_hash == cf_hash, "Hash of CountedFloat should match the hash of the underlying float value."


@pytest.mark.parametrize("f", [-1.0, 0.0, math.pi, math.e])
def test_counted_float_str_repr(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    cf_str = str(cf)
    cf_repr = repr(cf)

    # --- assert ------------------------------------------
    assert cf_str == f"CountedFloat({f!s})", "String representation of CountedFloat is incorrect."
    assert cf_repr == f"CountedFloat({f!r})", "Repr representation of CountedFloat is incorrect."


def test_counted_float_refuses_attribute_assignment_like_plain_float():
    """Empty slots enforce the drop-in-float contract: no per-instance attributes."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.5)

    # --- act / assert ------------------------------------
    with pytest.raises(AttributeError):
        (1.5).attr = 1  # ty: ignore[unresolved-attribute] -- pinning plain float's refusal
    with pytest.raises(AttributeError):
        cf.attr = 1  # ty: ignore[unresolved-attribute] -- must refuse exactly like plain float
    assert not hasattr(cf, "__dict__")


def test_counted_float_refuses_weak_references_like_plain_float():
    """Empty slots enforce the drop-in-float contract: no weak references."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.5)

    # --- act / assert ------------------------------------
    with pytest.raises(TypeError):
        weakref.ref(1.5)
    with pytest.raises(TypeError):
        weakref.ref(cf)


# =================================================================================================
#  CountedFloat - Correct math operations
# =================================================================================================
@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_abs(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_abs = abs(f)
    cf_abs = abs(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_abs, CountedFloat)
    assert f_abs == cf_abs


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_neg(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_neg = -f
    cf_neg = -cf

    # --- assert ------------------------------------------
    assert isinstance(cf_neg, CountedFloat)
    assert f_neg == cf_neg


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_eq(f1: float, f2: float):
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(f1)
    cf2 = CountedFloat(f2)

    # --- act ---------------------------------------------
    f_eq = f1 == f2
    cf_eq = cf1 == cf2

    # --- assert ------------------------------------------
    assert isinstance(cf_eq, bool)
    assert f_eq == cf_eq


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_eq_zero(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_eq_zero = f == 0
    cf_eq_zero = cf == 0

    # --- assert ------------------------------------------
    assert isinstance(cf_eq_zero, bool)
    assert f_eq_zero == cf_eq_zero


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_ne(f1: float, f2: float):
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(f1)
    cf2 = CountedFloat(f2)

    # --- act ---------------------------------------------
    f_ne = f1 != f2
    cf_ne = cf1 != cf2

    # --- assert ------------------------------------------
    assert isinstance(cf_ne, bool)
    assert f_ne == cf_ne


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_ne_zero(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_ne_zero = f != 0
    cf_ne_zero = cf != 0

    # --- assert ------------------------------------------
    assert isinstance(cf_ne_zero, bool)
    assert f_ne_zero == cf_ne_zero


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_lt(f1: float, f2: float):
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(f1)
    cf2 = CountedFloat(f2)

    # --- act ---------------------------------------------
    f_lt = f1 < f2
    cf_lt = cf1 < cf2

    # --- assert ------------------------------------------
    assert isinstance(cf_lt, bool)
    assert f_lt == cf_lt


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_lt_zero(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_lt_zero = f < 0
    cf_lt_zero = cf < 0

    # --- assert ------------------------------------------
    assert isinstance(cf_lt_zero, bool)
    assert f_lt_zero == cf_lt_zero


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_le(f1: float, f2: float):
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(f1)
    cf2 = CountedFloat(f2)

    # --- act ---------------------------------------------
    f_le = f1 <= f2
    cf_le = cf1 <= cf2

    # --- assert ------------------------------------------
    assert isinstance(cf_le, bool)
    assert f_le == cf_le


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_le_zero(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_le_zero = f <= 0
    cf_le_zero = cf <= 0

    # --- assert ------------------------------------------
    assert isinstance(cf_le_zero, bool)
    assert f_le_zero == cf_le_zero


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_gt(f1: float, f2: float):
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(f1)
    cf2 = CountedFloat(f2)

    # --- act ---------------------------------------------
    f_gt = f1 > f2
    cf_gt = cf1 > cf2

    # --- assert ------------------------------------------
    assert isinstance(cf_gt, bool)
    assert f_gt == cf_gt


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_gt_zero(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_gt_zero = f > 0
    cf_gt_zero = cf > 0

    # --- assert ------------------------------------------
    assert isinstance(cf_gt_zero, bool)
    assert f_gt_zero == cf_gt_zero


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_ge(f1: float, f2: float):
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(f1)
    cf2 = CountedFloat(f2)

    # --- act ---------------------------------------------
    f_ge = f1 >= f2
    cf_ge = cf1 >= cf2

    # --- assert ------------------------------------------
    assert isinstance(cf_ge, bool)
    assert f_ge == cf_ge


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_ge_zero(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_ge_zero = f >= 0
    cf_ge_zero = cf >= 0

    # --- assert ------------------------------------------
    assert isinstance(cf_ge_zero, bool)
    assert f_ge_zero == cf_ge_zero


@pytest.mark.parametrize("n_digits", [0, 1])
@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_round_n(f: float, n_digits: int):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)
    # --- act ---------------------------------------------
    f_round = round(f, n_digits)
    cf_round = round(cf, n_digits)

    # --- assert ------------------------------------------
    assert isinstance(cf_round, float)
    assert f_round == cf_round


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_round(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)
    # --- act ---------------------------------------------
    f_round = round(f)
    cf_round = round(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_round, int)
    assert f_round == cf_round


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_floor(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_floor = math.floor(f)
    cf_floor = math.floor(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_floor, int)
    assert f_floor == cf_floor


@pytest.mark.parametrize("f", [-1.0, 0.0, -math.pi, math.e])
def test_counted_float_math_ceil(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_ceil = math.ceil(f)
    cf_ceil = math.ceil(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_ceil, int)
    assert f_ceil == cf_ceil


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize(("cf_left", "cf_right"), [(False, True), (True, False), (True, True)])
def test_counted_float_math_add(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    left = CountedFloat(f1) if cf_left else f1

    right = CountedFloat(f2) if cf_right else f2

    # --- act ---------------------------------------------
    f_sum = f1 + f2
    cf_sum = left + right

    # --- assert ------------------------------------------
    assert isinstance(cf_sum, CountedFloat)
    assert f_sum == cf_sum


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize(("cf_left", "cf_right"), [(False, True), (True, False), (True, True)])
def test_counted_float_math_sub(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    left = CountedFloat(f1) if cf_left else f1

    right = CountedFloat(f2) if cf_right else f2

    # --- act ---------------------------------------------
    f_diff = f1 - f2
    cf_diff = left - right

    # --- assert ------------------------------------------
    assert isinstance(cf_diff, CountedFloat)
    assert f_diff == cf_diff


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize(("cf_left", "cf_right"), [(False, True), (True, False), (True, True)])
def test_counted_float_math_mul(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    left = CountedFloat(f1) if cf_left else f1

    right = CountedFloat(f2) if cf_right else f2

    # --- act ---------------------------------------------
    f_prod = f1 * f2
    cf_prod = left * right

    # --- assert ------------------------------------------
    assert isinstance(cf_prod, CountedFloat)
    assert f_prod == cf_prod


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, -math.pi, math.e])
@pytest.mark.parametrize(("cf_left", "cf_right"), [(False, True), (True, False), (True, True)])
def test_counted_float_math_div(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    left = CountedFloat(f1) if cf_left else f1

    right = CountedFloat(f2) if cf_right else f2

    # --- act ---------------------------------------------
    f_ratio = f1 / f2
    cf_ratio = left / right

    # --- assert ------------------------------------------
    assert isinstance(cf_ratio, CountedFloat)
    assert f_ratio == cf_ratio


@pytest.mark.parametrize("f1", [0.0, 1.0, 2, math.e])
@pytest.mark.parametrize("f2", [0.0, 1.0, 2, math.pi])
@pytest.mark.parametrize(("cf_left", "cf_right"), [(False, True), (True, False), (True, True)])
def test_counted_float_math_pow(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    left = CountedFloat(f1) if cf_left else f1

    right = CountedFloat(f2) if cf_right else f2

    # --- act ---------------------------------------------
    f_pow = f1**f2
    cf_pow = left**right

    # --- assert ------------------------------------------
    assert isinstance(cf_pow, CountedFloat)
    assert f_pow == cf_pow


@pytest.mark.parametrize("f", [0.0, 1.0, 2.0, math.e])
def test_counted_float_math_sqrt(thread_counter, f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_sqrt = math.sqrt(f)
    cf_sqrt = math.sqrt(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_sqrt, CountedFloat)
    assert f_sqrt == cf_sqrt


@pytest.mark.parametrize("f", [1.0, 2.0, math.e])
def test_counted_float_math_log2(thread_counter, f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_log2 = math.log2(f)
    cf_log2 = math.log2(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_log2, CountedFloat)
    assert f_log2 == cf_log2


# =================================================================================================
#  CountedFloat - Correct integration with THREAD_COUNTER
# =================================================================================================
@pytest.mark.parametrize(
    ("value", "expected_n_i2f"),
    [
        (0, 1),
        (1, 1),
        (-1, 1),
        (3.14159, 0),
        (-3.14159, 0),
        (math.e, 0),
        (-math.e, 0),
    ],
)
def test_counted_float_construction(value: float | int, expected_n_i2f: int, thread_counter):
    # --- act ---------------------------------------------
    CountedFloat(value)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == expected_n_i2f
    assert expected_n_i2f == thread_counter.I2F


def test_counted_float_counts_abs(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = abs(cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.ABS == 1


def test_counted_float_counts_neg(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = -cf

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.MINUS == 1


def test_counted_float_counts_eq(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf == 0
    _ = cf == 1
    _ = cf == 0.0
    _ = cf == 1.23456
    _ = cf == 2.34567

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.COMP == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_ne(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf != 0
    _ = cf != 1
    _ = cf != 0.0
    _ = cf != 1.23456
    _ = cf != 2.34567

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.COMP == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_lt(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf < 0
    _ = cf < 1
    _ = cf < 0.0
    _ = cf < 1.23456
    _ = cf < 2.34567

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.COMP == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_le(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf <= 0
    _ = cf <= 1
    _ = cf <= 0.0
    _ = cf <= 1.23456
    _ = cf <= 2.34567

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.COMP == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_gt(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf > 0
    _ = cf > 1
    _ = cf > 0.0
    _ = cf > 1.23456
    _ = cf > 2.34567

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.COMP == 5
    assert thread_counter.I2F == 0


@pytest.mark.parametrize("min_max_fun", [min, max])
@pytest.mark.parametrize(
    ("f1", "f2"),
    [(1.2345, 0.1234), (0.345, 0.222), (2.468, 2.468), (2.468, 2), (3, 2.478), (2, 3)],
)
@pytest.mark.parametrize(("cf_left", "cf_right"), [(False, True), (True, False), (True, True)])
def test_counted_float_counts_min_max(
    min_max_fun: Callable, f1: float, f2: float, cf_left: bool, cf_right: bool, thread_counter
):
    # --- arrange -----------------------------------------
    expected_i2f = int(cf_left and isinstance(f1, int)) + int(cf_right and isinstance(f2, int))
    left = CountedFloat(f1) if cf_left else f1

    right = CountedFloat(f2) if cf_right else f2

    # --- act ---------------------------------------------
    f_min_max = min_max_fun(f1, f2)
    cf_min_max = min_max_fun(left, right)

    # --- assert ------------------------------------------
    assert thread_counter.COMP == 1
    assert expected_i2f == thread_counter.I2F
    assert f_min_max == cf_min_max


def test_counted_float_counts_ge(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf >= 0
    _ = cf >= 1
    _ = cf >= 0.0
    _ = cf >= 1.23456
    _ = cf >= 2.34567

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.COMP == 5
    assert thread_counter.I2F == 0


@pytest.mark.parametrize(
    ("ndigits", "expected_counts"),
    [
        (None, {"F2I": 1}),  # round to int -> F2I
        (0, {"RND": 1}),  # round to nearest integer, return float -> RND
        (1, {"MUL": 1, "RND": 1, "DIV": 1}),  # scale, round, unscale
        (2, {"MUL": 1, "RND": 1, "DIV": 1}),
        (-3, {"MUL": 1, "RND": 1, "DIV": 1}),  # negative digit counts scale the other way
    ],
)
def test_counted_float_counts_round(thread_counter, ndigits, expected_counts: dict[str, int]):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = round(cf, ndigits)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == sum(expected_counts.values())
    for field, expected in expected_counts.items():
        assert getattr(thread_counter, field) == expected


def test_counted_float_counts_floor(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.floor(cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.F2I == 1


def test_counted_float_counts_ceil(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.ceil(cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.F2I == 1


def test_counted_float_counts_int(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = int(cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.F2I == 1


def test_counted_float_counts_trunc(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.trunc(cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.F2I == 1


def test_counted_float_counts_add(thread_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f + cf
    _ = cf + f
    _ = cf + cf
    _ = (cf + f) + f

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.ADD == 5


def test_counted_float_counts_add_int(thread_counter):
    # --- arrange -----------------------------------------
    i = 3
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = i + cf
    _ = cf + i
    _ = cf + cf
    _ = (cf + i) + i

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.ADD == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_sub(thread_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f - cf
    _ = cf - f
    _ = cf - cf
    _ = (cf - f) - f

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.SUB == 5


def test_counted_float_counts_sub_int(thread_counter):
    # --- arrange -----------------------------------------
    i = 3
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = i - cf
    _ = cf - i
    _ = cf - cf
    _ = (cf - i) - i

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.SUB == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_mul(thread_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f * cf
    _ = cf * f
    _ = cf * cf
    _ = (cf * f) * f

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.MUL == 5


def test_counted_float_counts_mul_int(thread_counter):
    # --- arrange -----------------------------------------
    i = 3
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = i * cf
    _ = cf * i
    _ = cf * cf
    _ = (cf * i) * i

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.MUL == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_div(thread_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f / cf
    _ = cf / f
    _ = cf / cf
    _ = (cf / f) / f

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.DIV == 5


def test_counted_float_counts_div_int(thread_counter):
    # --- arrange -----------------------------------------
    i = 3
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = i / cf
    _ = cf / i
    _ = cf / cf
    _ = (cf / i) / i

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 5
    assert thread_counter.DIV == 5
    assert thread_counter.I2F == 0


@pytest.mark.parametrize(
    ("divisor", "expected_counts"),
    [
        (2.0, {"MUL": 1}),
        (0.5, {"MUL": 1}),
        (-8.0, {"MUL": 1}),  # sign carries into the reciprocal; the fold still applies
        (4, {"MUL": 1}),  # an int and an equal-valued plain float compile identically
        (1.0, {}),  # folds away entirely, like x ** 1
        (1, {}),
        (-1.0, {"MUL": 1}),  # only exact identity folds to nothing; the sign flip keeps its MUL
        (2.0**-1023, {"MUL": 1}),  # smallest power of two whose reciprocal is finite
        (2.0**-1024, {"DIV": 1}),  # reciprocal overflows -> fold not value-preserving
        (3.0, {"DIV": 1}),
        (0.1, {"DIV": 1}),
        (6.0, {"DIV": 1}),  # even, but not a power of two
        (float("inf"), {"DIV": 1}),
        (float("nan"), {"DIV": 1}),
    ],
)
def test_counted_float_counts_div_by_constant(thread_counter, divisor, expected_counts: dict[str, int]):
    """x / c with a power-of-two constant c counts the reciprocal multiply a compiler emits."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf / divisor

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == sum(expected_counts.values())
    for field, expected in expected_counts.items():
        assert getattr(thread_counter, field) == expected


def test_counted_float_counts_div_by_dynamic_power_of_two_as_div(thread_counter):
    """The reciprocal fold keys on the divisor being constant: a CountedFloat divisor stays DIV."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf / CountedFloat(2.0)  # dynamic divisor, even though its value is a power of two
    _ = 2.0 / cf  # reflected form: the divisor is the CountedFloat, dynamic as well

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 2
    assert thread_counter.DIV == 2


def test_counted_float_counts_pow_1(thread_counter):
    # --- arrange -----------------------------------------
    i = 9
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f**cf  # POW
    _ = cf**f  # POW
    _ = (cf**f) ** f  # 2 x POW
    _ = (f**cf) ** f  # 2 x POW
    _ = cf**cf  # POW
    _ = math.exp(cf)  # EXP
    _ = 2**cf  # EXP2
    _ = math.exp2(cf)  # EXP2
    _ = 10**cf  # EXP10
    _ = cf**2  # MUL
    _ = i**cf  # POW
    _ = cf**i  # 4 x MUL (i == 9: square-and-multiply)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 17
    assert thread_counter.POW == 8
    assert thread_counter.EXP == 1
    assert thread_counter.EXP2 == 2
    assert thread_counter.EXP10 == 1
    assert thread_counter.MUL == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_pow_2(thread_counter):
    # --- arrange -----------------------------------------
    i = 9
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.pow(f, cf)  # POW
    _ = math.pow(cf, f)  # POW
    _ = math.pow(math.pow(cf, f), f)  # 2 x POW
    _ = math.pow(math.pow(f, cf), f)  # 2 x POW
    _ = math.pow(cf, cf)  # POW
    _ = math.pow(2, cf)  # EXP2
    _ = math.pow(10, cf)  # EXP10
    _ = math.pow(cf, 2)  # MUL
    _ = math.pow(i, cf)  # POW
    _ = math.pow(cf, i)  # 4 x MUL (i == 9: square-and-multiply)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 15
    assert thread_counter.POW == 8
    assert thread_counter.EXP2 == 1
    assert thread_counter.EXP10 == 1
    assert thread_counter.MUL == 5
    assert thread_counter.I2F == 0


def test_counted_float_counts_sqrt(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.sqrt(cf)
    # NOTE: The below is not counted; such simple expressions can often be precomputed and shipped as a constant.
    #       If this needs to be counted, first convert to CountedFloat.
    _ = math.sqrt(3)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.SQRT == 1


def test_counted_float_counts_cbrt(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.cbrt(cf)
    # NOTE: The below is not counted; such simple expressions can often be precomputed and shipped as a constant.
    #       If this needs to be counted, first convert to CountedFloat.
    _ = math.cbrt(3)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.CBRT == 1


def test_counted_float_counts_log(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.log(cf)
    _ = math.log2(cf)
    _ = math.log10(cf)
    # NOTE: The below is not counted; such simple expressions can often be precomputed and shipped as a constant.
    #       If this needs to be counted, first convert to CountedFloat.
    _ = math.log2(3)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 3
    assert thread_counter.LOG == 1
    assert thread_counter.LOG2 == 1
    assert thread_counter.LOG10 == 1


def test_counted_float_counts_sin_cos_tan(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.sin(cf)

    _ = math.cos(cf)
    _ = math.cos(cf)

    _ = math.tan(cf)
    _ = math.tan(cf)
    _ = math.tan(cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 6
    assert thread_counter.SIN == 1
    assert thread_counter.COS == 2
    assert thread_counter.TAN == 3


# =================================================================================================
#  CountedFloat - %, //, divmod, unary + (contagion completion)
# =================================================================================================
def test_counted_float_counts_floordiv(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(7.5)

    # --- act ---------------------------------------------
    forward = cf // 2.0
    reflected = 17.0 // cf

    # --- assert ------------------------------------------
    # values compared via float() so the comparison itself does not count a COMP
    assert isinstance(forward, CountedFloat)
    assert isinstance(reflected, CountedFloat)
    assert (float(forward), float(reflected)) == (3.0, 2.0)
    assert thread_counter.DIV == 2  # each // counts DIV + RND
    assert thread_counter.RND == 2
    assert thread_counter.total_count() == 4


def test_counted_float_counts_mod(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(7.5)

    # --- act ---------------------------------------------
    forward = cf % 2.0
    reflected = 17.0 % cf

    # --- assert ------------------------------------------
    assert isinstance(forward, CountedFloat)
    assert isinstance(reflected, CountedFloat)
    assert (float(forward), float(reflected)) == (1.5, 2.0)
    # each % counts the floored-remainder decomposition DIV + RND + MUL + SUB
    assert thread_counter.DIV == 2
    assert thread_counter.RND == 2
    assert thread_counter.MUL == 2
    assert thread_counter.SUB == 2
    assert thread_counter.total_count() == 8


def test_counted_float_counts_divmod(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(7.5)

    # --- act ---------------------------------------------
    q, r = divmod(cf, 2.0)
    rq, rr = divmod(17.0, cf)

    # --- assert ------------------------------------------
    assert isinstance(q, CountedFloat)
    assert isinstance(r, CountedFloat)
    assert isinstance(rq, CountedFloat)
    assert isinstance(rr, CountedFloat)
    assert (float(q), float(r)) == (3.0, 1.5)
    # each divmod shares the quotient's DIV + RND with the remainder: DIV + RND + MUL + SUB per call
    assert thread_counter.DIV == 2
    assert thread_counter.RND == 2
    assert thread_counter.MUL == 2
    assert thread_counter.SUB == 2
    assert thread_counter.total_count() == 8


def test_counted_float_unary_plus_preserves_type_and_counts_nothing(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    result = +cf

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert float(result) == 1.23456
    assert thread_counter.total_count() == 0


@pytest.mark.parametrize("op", [operator.floordiv, operator.mod, divmod])
def test_counted_float_mod_floordiv_divmod_zero_division_counts_nothing(thread_counter, op: Callable):
    # --- arrange -----------------------------------------
    cf = CountedFloat(7.5)
    cf_zero = CountedFloat(0.0)  # construction from a float counts nothing

    # --- act & assert ------------------------------------
    with pytest.raises(ZeroDivisionError):
        op(cf, 0.0)  # forward path: cf // 0.0
    with pytest.raises(ZeroDivisionError):
        op(17.0, cf_zero)  # reflected path: 17.0 // cf_zero
    assert thread_counter.total_count() == 0


@pytest.mark.parametrize(
    ("exponent", "expected_counts"),
    [
        (0, {}),  # folds away entirely
        (1, {}),
        (2, {"MUL": 1}),
        (2.0, {"MUL": 1}),  # constants fold by value: 2.0 compiles like 2
        (3, {"MUL": 2}),  # x*x, *x
        (4, {"MUL": 2}),  # square twice
        (8, {"MUL": 3}),
        (9, {"MUL": 4}),
        (16, {"MUL": 4}),
        (-1, {"DIV": 1}),  # reciprocal
        (-3, {"MUL": 2, "DIV": 1}),
        (0.5, {"SQRT": 1}),
        (-0.5, {"SQRT": 1, "DIV": 1}),
        (17, {"POW": 1}),  # beyond the powi cutoff
        (-17, {"POW": 1}),
        (2.5, {"POW": 1}),  # non-integral, non-special value
        (math.nan, {"POW": 1}),
    ],
)
def test_counted_float_pow_constant_exponent_strength_reduction(thread_counter, exponent, expected_counts):
    """A constant exponent counts what a compiled port would emit, folded by value."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    result = cf**exponent

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert thread_counter.total_count() == sum(expected_counts.values())
    for flop_name, count in expected_counts.items():
        assert getattr(thread_counter, flop_name) == count


def test_counted_float_pow_strength_reduction_mirrored_in_math_pow(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.pow(cf, 0.5)  # SQRT
    _ = math.pow(cf, -1)  # DIV
    _ = math.pow(cf, 3)  # 2 x MUL
    _ = math.pow(2.0, cf)  # EXP2 (constant base folds by value)
    _ = math.pow(10.0, cf)  # EXP10

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 6
    assert thread_counter.SQRT == 1
    assert thread_counter.DIV == 1
    assert thread_counter.MUL == 2
    assert thread_counter.EXP2 == 1
    assert thread_counter.EXP10 == 1


def test_counted_float_rpow_constant_float_base_folds_by_value(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = 2.0**cf  # EXP2
    _ = 10.0**cf  # EXP10
    _ = 3.0**cf  # POW

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 3
    assert thread_counter.EXP2 == 1
    assert thread_counter.EXP10 == 1
    assert thread_counter.POW == 1


def test_counted_float_pow_runtime_counted_exponent_counts_pow(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf ** CountedFloat(2.0)  # a CountedFloat exponent is genuinely runtime: no folding

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.POW == 1
