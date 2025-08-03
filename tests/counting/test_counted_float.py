import math
from typing import Callable

import pytest

from counted_float._core.counting._counted_float import CountedFloat
from counted_float._core.counting.models import FlopCounts


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
    assert cf_str == f"CountedFloat({str(f)})", "String representation of CountedFloat is incorrect."
    assert cf_repr == f"CountedFloat({repr(f)})", "Repr representation of CountedFloat is incorrect."


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


def test_counted_float_math_round_value_error():
    # --- arrange -----------------------------------------
    cf = CountedFloat(math.pi)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):
        round(cf, 2)  # not supported by CountedFloat


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
@pytest.mark.parametrize("cf_left, cf_right", [(False, True), (True, False), (True, True)])
def test_counted_float_math_add(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    if cf_left:
        left = CountedFloat(f1)
    else:
        left = f1

    if cf_right:
        right = CountedFloat(f2)
    else:
        right = f2

    # --- act ---------------------------------------------
    f_sum = f1 + f2
    cf_sum = left + right

    # --- assert ------------------------------------------
    assert isinstance(cf_sum, CountedFloat)
    assert f_sum == cf_sum


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("cf_left, cf_right", [(False, True), (True, False), (True, True)])
def test_counted_float_math_sub(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    if cf_left:
        left = CountedFloat(f1)
    else:
        left = f1

    if cf_right:
        right = CountedFloat(f2)
    else:
        right = f2

    # --- act ---------------------------------------------
    f_diff = f1 - f2
    cf_diff = left - right

    # --- assert ------------------------------------------
    assert isinstance(cf_diff, CountedFloat)
    assert f_diff == cf_diff


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("cf_left, cf_right", [(False, True), (True, False), (True, True)])
def test_counted_float_math_mul(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    if cf_left:
        left = CountedFloat(f1)
    else:
        left = f1

    if cf_right:
        right = CountedFloat(f2)
    else:
        right = f2

    # --- act ---------------------------------------------
    f_prod = f1 * f2
    cf_prod = left * right

    # --- assert ------------------------------------------
    assert isinstance(cf_prod, CountedFloat)
    assert f_prod == cf_prod


@pytest.mark.parametrize("f1", [-1.0, 0.0, -math.pi, math.e])
@pytest.mark.parametrize("f2", [-1.0, -math.pi, math.e])
@pytest.mark.parametrize("cf_left, cf_right", [(False, True), (True, False), (True, True)])
def test_counted_float_math_div(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    if cf_left:
        left = CountedFloat(f1)
    else:
        left = f1

    if cf_right:
        right = CountedFloat(f2)
    else:
        right = f2

    # --- act ---------------------------------------------
    f_ratio = f1 / f2
    cf_ratio = left / right

    # --- assert ------------------------------------------
    assert isinstance(cf_ratio, CountedFloat)
    assert f_ratio == cf_ratio


@pytest.mark.parametrize("f1", [0.0, 1.0, 2, math.e])
@pytest.mark.parametrize("f2", [0.0, 1.0, 2, math.pi])
@pytest.mark.parametrize("cf_left, cf_right", [(False, True), (True, False), (True, True)])
def test_counted_float_math_pow(f1: float, f2: float, cf_left: bool, cf_right: bool):
    # --- arrange -----------------------------------------
    if cf_left:
        left = CountedFloat(f1)
    else:
        left = f1

    if cf_right:
        right = CountedFloat(f2)
    else:
        right = f2

    # --- act ---------------------------------------------
    f_pow = f1**f2
    cf_pow = left**right

    # --- assert ------------------------------------------
    assert isinstance(cf_pow, CountedFloat)
    assert f_pow == cf_pow


@pytest.mark.parametrize("f", [0.0, 1.0, 2.0, math.e])
def test_counted_float_math_sqrt(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_sqrt = math.sqrt(f)
    cf_sqrt = math.sqrt(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_sqrt, CountedFloat)
    assert f_sqrt == cf_sqrt


@pytest.mark.parametrize("f", [1.0, 2.0, math.e])
def test_counted_float_math_log2(f: float):
    # --- arrange -----------------------------------------
    cf = CountedFloat(f)

    # --- act ---------------------------------------------
    f_log2 = math.log2(f)
    cf_log2 = math.log2(cf)

    # --- assert ------------------------------------------
    assert isinstance(cf_log2, CountedFloat)
    assert f_log2 == cf_log2


# =================================================================================================
#  CountedFloat - Correct integration with GLOBAL_COUNTER
# =================================================================================================
def test_counted_float_get_global_flop_counts(global_counter):
    # --- arrange -----------------------------------------
    global_counter.incr_add()
    global_counter.incr_add()

    # --- act ---------------------------------------------
    global_flop_counts = CountedFloat.get_global_flop_counts()
    global_counter.incr_add()  # to double-check we get a copy

    # --- assert ------------------------------------------
    assert isinstance(global_flop_counts, FlopCounts)
    assert global_flop_counts.total_count() == 2
    assert global_flop_counts.ADD == 2


def test_counted_float_counts_abs(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = abs(cf)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.ABS == 1


def test_counted_float_counts_neg(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = -cf

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.MINUS == 1


def test_counted_float_counts_eq(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf == 0
    _ = cf == 0.0
    _ = cf == 1.23456
    _ = cf == 2.34567

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 4
    assert global_counter.CMP_ZERO == 1
    assert global_counter.EQUALS == 3


def test_counted_float_counts_ne(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf != 0
    _ = cf != 0.0
    _ = cf != 1.23456
    _ = cf != 2.34567

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 4
    assert global_counter.CMP_ZERO == 1
    assert global_counter.EQUALS == 3


def test_counted_float_counts_lt(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf < 0
    _ = cf < 0.0
    _ = cf < 1.23456
    _ = cf < 2.34567

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 4
    assert global_counter.CMP_ZERO == 1
    assert global_counter.LTE == 3


def test_counted_float_counts_le(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf <= 0
    _ = cf <= 0.0
    _ = cf <= 1.23456
    _ = cf <= 2.34567

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 4
    assert global_counter.CMP_ZERO == 1
    assert global_counter.LTE == 3


def test_counted_float_counts_gt(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf > 0
    _ = cf > 0.0
    _ = cf > 1.23456
    _ = cf > 2.34567

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 4
    assert global_counter.CMP_ZERO == 1
    assert global_counter.GTE == 3


@pytest.mark.parametrize("min_max_fun", [min, max])
@pytest.mark.parametrize("f1, f2", [(1.2345, 0.1234), (0.345, 0.222), (2.468, 2.468)])
@pytest.mark.parametrize("cf_left, cf_right", [(False, True), (True, False), (True, True)])
def test_counted_float_counts_min_max(
    min_max_fun: Callable, f1: float, f2: float, cf_left: bool, cf_right: bool, global_counter
):
    # --- arrange -----------------------------------------
    if cf_left:
        left = CountedFloat(f1)
    else:
        left = f1

    if cf_right:
        right = CountedFloat(f2)
    else:
        right = f2

    # --- act ---------------------------------------------
    f_min_max = min_max_fun(f1, f2)
    cf_min_max = min_max_fun(left, right)

    # --- assert ------------------------------------------
    assert global_counter.LTE + global_counter.GTE == 1
    assert f_min_max == cf_min_max


def test_counted_float_counts_ge(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = cf >= 0
    _ = cf >= 0.0
    _ = cf >= 1.23456
    _ = cf >= 2.34567

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 4
    assert global_counter.CMP_ZERO == 1
    assert global_counter.GTE == 3


def test_counted_float_counts_round(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = round(cf)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.RND == 1


def test_counted_float_counts_floor(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.floor(cf)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.RND == 1


def test_counted_float_counts_ceil(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.ceil(cf)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.RND == 1


def test_counted_float_counts_add(global_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f + cf
    _ = cf + f
    _ = cf + cf
    _ = (cf + f) + f

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 5
    assert global_counter.ADD == 5


def test_counted_float_counts_sub(global_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f - cf
    _ = cf - f
    _ = cf - cf
    _ = (cf - f) - f

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 5
    assert global_counter.SUB == 5


def test_counted_float_counts_mul(global_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f * cf
    _ = cf * f
    _ = cf * cf
    _ = (cf * f) * f

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 5
    assert global_counter.MUL == 5


def test_counted_float_counts_div(global_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f / cf
    _ = cf / f
    _ = cf / cf
    _ = (cf / f) / f

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 5
    assert global_counter.DIV == 5


def test_counted_float_counts_pow_1(global_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = f**cf  # POW
    _ = cf**f  # POW
    _ = (cf**f) ** f  # 2 x POW
    _ = (f**cf) ** f  # 2 x POW
    _ = cf**cf  # POW
    _ = 2**cf  # POW2
    _ = cf**2  # MUL

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 9
    assert global_counter.POW == 7
    assert global_counter.POW2 == 1
    assert global_counter.MUL == 1


def test_counted_float_counts_pow_2(global_counter):
    # --- arrange -----------------------------------------
    f = 3.14159
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.pow(f, cf)  # POW
    _ = math.pow(cf, f)  # POW
    _ = math.pow(math.pow(cf, f), f)  # 2 x POW
    _ = math.pow(math.pow(f, cf), f)  # 2 x POW
    _ = math.pow(cf, cf)  # POW
    _ = math.pow(2, cf)  # POW2
    _ = math.pow(cf, 2)  # MUL

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 9
    assert global_counter.POW == 7
    assert global_counter.POW2 == 1
    assert global_counter.MUL == 1


def test_counted_float_counts_sqrt(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.sqrt(cf)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.SQRT == 1


def test_counted_float_counts_log2(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = math.log2(cf)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.LOG2 == 1
