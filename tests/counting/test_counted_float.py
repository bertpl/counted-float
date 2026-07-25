import math
import weakref

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


def test_counted_float_refuses_subclassing():
    """Sealed for type checkers and at runtime: no operator can carry a subtype through."""
    # --- act / assert ------------------------------------
    with pytest.raises(TypeError, match="does not support subclassing"):
        type("Tagged", (CountedFloat,), {"__slots__": ()})
    assert CountedFloat.__final__ is True  # the marker @final leaves for type checkers


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
