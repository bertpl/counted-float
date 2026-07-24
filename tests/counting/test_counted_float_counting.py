import math
import operator
from collections.abc import Callable

import pytest

from counted_float._core.counting._counted_float import CountedFloat


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
        (-1.0, {"MINUS": 1}),  # x / -1.0 is exactly -x: a bare sign flip, not a multiply
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


@pytest.mark.parametrize(
    ("case", "expected_counts"),
    [
        # --- folds: the compiled port emits nothing (cost-model rule 1.7) ---
        (lambda cf: cf * 1.0, {}),
        (lambda cf: 1.0 * cf, {}),
        (lambda cf: cf * 1, {}),  # an int and an equal-valued plain float compile identically
        (lambda cf: cf - 0.0, {}),
        (lambda cf: cf - 0, {}),  # int 0 compiles as +0.0
        (lambda cf: cf + (-0.0), {}),
        (lambda cf: (-0.0) + cf, {}),
        # --- sign flips: exactly -x, so MINUS ---
        (lambda cf: cf * -1.0, {"MINUS": 1}),
        (lambda cf: -1.0 * cf, {"MINUS": 1}),
        (lambda cf: cf * -1, {"MINUS": 1}),
        (lambda cf: (-0.0) - cf, {"MINUS": 1}),
        (lambda cf: cf / -1.0, {"MINUS": 1}),
        # --- sharp near-misses: a signed zero makes these value-changing, so they keep counting ---
        (lambda cf: cf + 0.0, {"ADD": 1}),  # -0.0 + 0.0 is +0.0
        (lambda cf: cf + 0, {"ADD": 1}),
        (lambda cf: 0.0 + cf, {"ADD": 1}),
        (lambda cf: cf - (-0.0), {"SUB": 1}),  # it IS x + 0.0
        (lambda cf: 0.0 - cf, {"SUB": 1}),  # 0.0 - 0.0 is +0.0, not the sign flip's -0.0
        (lambda cf: 0 - cf, {"SUB": 1}),
        # --- decomposed operations: the division step folds like a bare / ---
        (lambda cf: cf // 8.0, {"RND": 1, "MUL": 1}),
        (lambda cf: cf // 1.0, {"RND": 1}),
        (lambda cf: cf // 3.0, {"DIV": 1, "RND": 1}),
        (lambda cf: cf % 8.0, {"RND": 1, "MUL": 2, "SUB": 1}),
        (lambda cf: cf % 3.0, {"DIV": 1, "RND": 1, "MUL": 1, "SUB": 1}),
        (lambda cf: divmod(cf, 4.0), {"RND": 1, "MUL": 2, "SUB": 1}),
        (lambda cf: divmod(cf, 3.0), {"DIV": 1, "RND": 1, "MUL": 1, "SUB": 1}),
    ],
)
def test_counted_float_identity_folds(thread_counter, case, expected_counts: dict[str, int]):
    """The sign-exact identity folds of cost-model rule 1.7, and the near-misses that must not fold."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = case(cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == sum(expected_counts.values())
    for field, expected in expected_counts.items():
        assert getattr(thread_counter, field) == expected


@pytest.mark.parametrize(
    ("case", "expected_counts"),
    [
        (lambda cf: cf * CountedFloat(1.0), {"MUL": 1}),
        (lambda cf: cf - CountedFloat(0.0), {"SUB": 1}),
        (lambda cf: cf + CountedFloat(-0.0), {"ADD": 1}),
        (lambda cf: cf / CountedFloat(-1.0), {"DIV": 1}),
        (lambda cf: cf // CountedFloat(8.0), {"DIV": 1, "RND": 1}),
        (lambda cf: cf % CountedFloat(8.0), {"DIV": 1, "RND": 1, "MUL": 1, "SUB": 1}),
    ],
)
def test_counted_float_identity_folds_key_on_constants_only(thread_counter, case, expected_counts):
    """The folds key on the operand being constant: a CountedFloat operand is dynamic, no fold."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.23456)

    # --- act ---------------------------------------------
    _ = case(cf)

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
    forward = cf // 3.0
    reflected = 17.0 // cf

    # --- assert ------------------------------------------
    # values compared via float() so the comparison itself does not count a COMP
    assert isinstance(forward, CountedFloat)
    assert isinstance(reflected, CountedFloat)
    assert (float(forward), float(reflected)) == (2.0, 2.0)
    assert thread_counter.DIV == 2  # each // counts DIV + RND (3.0 is not a foldable divisor)
    assert thread_counter.RND == 2
    assert thread_counter.total_count() == 4


def test_counted_float_counts_mod(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(7.5)

    # --- act ---------------------------------------------
    forward = cf % 3.0
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
    q, r = divmod(cf, 3.0)
    rq, rr = divmod(17.0, cf)

    # --- assert ------------------------------------------
    assert isinstance(q, CountedFloat)
    assert isinstance(r, CountedFloat)
    assert isinstance(rq, CountedFloat)
    assert isinstance(rr, CountedFloat)
    assert (float(q), float(r)) == (2.0, 1.5)
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


def test_counted_float_rpow_runtime_counted_base_counts_pow(thread_counter):
    # a CountedFloat base reaches __rpow__ as a genuinely runtime value -- a port computes
    # base ** x with no constant to fold, so a lone POW. Pin the absolute count so a
    # magnitude/field mutant on this branch is caught (a self-comparison of two runtime paths
    # would move alike on both sides and hide it)
    # --- act ---------------------------------------------
    result = CountedFloat(2.0).__rpow__(CountedFloat(3.0))  # base 3.0 ** exponent 2.0

    # --- assert ------------------------------------------
    assert float(result) == 9.0
    assert isinstance(result, CountedFloat)
    assert thread_counter.POW == 1
    assert thread_counter.total_count() == 1


@pytest.mark.parametrize(
    "method",
    ["__radd__", "__rsub__", "__rmul__", "__rtruediv__", "__rfloordiv__", "__rmod__", "__rdivmod__", "__rpow__"],
)
def test_reflected_op_returns_notimplemented_for_unsupported_operand(method: str) -> None:
    # a reflected dunder must defer (return NotImplemented) when the underlying float op cannot
    # handle the other operand, so Python can fall through to the operand's own handling / a TypeError
    # --- act ---------------------------------------------
    result = getattr(CountedFloat(2.0), method)("not a number")

    # --- assert ------------------------------------------
    assert result is NotImplemented


# =================================================================================================
#  CountedFloat - error-before-count invariant (a raising op counts nothing)
# =================================================================================================
def test_counted_float_construction_from_overflowing_int_counts_nothing(thread_counter):
    """An int too large to become a float raises before the I2F is counted -- no phantom flop."""
    # --- act / assert ------------------------------------
    with pytest.raises(OverflowError):
        CountedFloat(10**400)  # float(10**400) overflows; the I2F must not survive the raise

    assert thread_counter.total_count() == 0


@pytest.mark.parametrize(
    ("non_finite", "expected_exc"),
    [(float("inf"), OverflowError), (float("nan"), ValueError)],
    ids=["inf", "nan"],
)
@pytest.mark.parametrize(
    "convert",
    [int, math.floor, math.ceil, math.trunc, round],
    ids=["int", "floor", "ceil", "trunc", "round"],
)
def test_counted_float_non_finite_to_int_conversion_counts_nothing(
    thread_counter, convert: Callable, non_finite: float, expected_exc: type[Exception]
):
    """int/floor/ceil/trunc/round(x) of inf or nan raises before the F2I is counted -- no phantom flop."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(non_finite)  # construction from a float counts nothing

    # --- act / assert ------------------------------------
    with pytest.raises(expected_exc):
        convert(cf)

    assert thread_counter.total_count() == 0


# =================================================================================================
#  CountedFloat - the reflected return path carries the real value
# =================================================================================================
@pytest.mark.parametrize(
    ("case", "expected"),
    [
        (lambda cf: 5.0 - cf, 2.0),  # __rsub__ plain-minuend path: 5.0 - 3.0
        (lambda cf: (-0.0) - cf, -3.0),  # __rsub__ -0.0 sign-flip path: -(3.0)
        (lambda cf: divmod(17.0, cf), (5.0, 2.0)),  # __rdivmod__: (17 // 3, 17 % 3)
    ],
    ids=["rsub", "rsub_sign_flip", "rdivmod"],
)
def test_reflected_ops_carry_the_real_value(thread_counter, case: Callable, expected):
    # __rsub__ and __rdivmod__ rewrap their result(s) via float.__new__(CountedFloat, ...); the
    # count tests assert only the type, so a dropped result argument (a 0.0 return) would pass them.
    # --- arrange -----------------------------------------
    cf = CountedFloat(3.0)

    # --- act ---------------------------------------------
    result = case(cf)

    # --- assert ------------------------------------------
    if isinstance(expected, tuple):
        assert all(isinstance(r, CountedFloat) for r in result)
        assert tuple(float(r) for r in result) == expected
    else:
        assert isinstance(result, CountedFloat)
        assert float(result) == expected


# =================================================================================================
#  CountedFloat - counts accumulate across repeated calls
# =================================================================================================
# Each op is invoked twice from a fresh counter: a single-shot call (or a forward-then-reflected
# pair, where each path runs once) leaves the counting site at zero when it fires, so `field += 1`
# and `field = 1` are indistinguishable.  Each op is invoked n_calls times and the count asserted to
# reach n_calls x the per-call amount: n_calls == 1 pins the single-shot count, n_calls in (2, 5)
# forces the accumulating form.  The ops here are the single-shot paths not already covered elsewhere.
_ACCUMULATING_COUNTED_FLOAT_OPS = [
    ("neg", lambda: -CountedFloat(1.5), {"MINUS": 1}),
    ("abs", lambda: abs(CountedFloat(-1.5)), {"ABS": 1}),
    ("int", lambda: int(CountedFloat(1.5)), {"F2I": 1}),
    ("floor", lambda: math.floor(CountedFloat(1.5)), {"F2I": 1}),
    ("ceil", lambda: math.ceil(CountedFloat(1.5)), {"F2I": 1}),
    ("trunc", lambda: math.trunc(CountedFloat(1.5)), {"F2I": 1}),
    ("round_to_int", lambda: round(CountedFloat(1.5)), {"F2I": 1}),  # no ndigits -> F2I
    ("round_to_float", lambda: round(CountedFloat(1.5), 0), {"RND": 1}),
    ("round_to_digits", lambda: round(CountedFloat(1.5), 2), {"MUL": 1, "RND": 1, "DIV": 1}),
    ("floordiv", lambda: CountedFloat(7.5) // CountedFloat(3.0), {"DIV": 1, "RND": 1}),
    ("mod", lambda: CountedFloat(7.5) % CountedFloat(3.0), {"DIV": 1, "RND": 1, "MUL": 1, "SUB": 1}),
    ("divmod", lambda: divmod(CountedFloat(7.5), CountedFloat(3.0)), {"DIV": 1, "RND": 1, "MUL": 1, "SUB": 1}),
    ("rsub", lambda: 5.0 - CountedFloat(3.0), {"SUB": 1}),  # __rsub__ plain-minuend path
    ("rsub_sign_flip", lambda: (-0.0) - CountedFloat(3.0), {"MINUS": 1}),  # __rsub__ -0.0 minuend fold
    ("pow_sqrt", lambda: CountedFloat(2.0) ** 0.5, {"SQRT": 1}),  # count_pow_with_constant_exponent
    ("pow_sqrt_reciprocal", lambda: CountedFloat(2.0) ** -0.5, {"SQRT": 1, "DIV": 1}),  # -0.5 branch
    ("pow_reciprocal", lambda: CountedFloat(2.0) ** -1, {"DIV": 1}),
    ("pow_powi", lambda: CountedFloat(2.0) ** 3, {"MUL": 2}),  # square-and-multiply chain
    ("pow_neg_powi", lambda: CountedFloat(2.0) ** -3, {"MUL": 2, "DIV": 1}),
    ("rpow_exp2", lambda: 2.0 ** CountedFloat(3.0), {"EXP2": 1}),  # count_pow_with_constant_base
    ("rpow_exp10", lambda: 10.0 ** CountedFloat(3.0), {"EXP10": 1}),
    ("rpow_runtime_base", lambda: CountedFloat(2.0).__rpow__(CountedFloat(3.0)), {"POW": 1}),  # __rpow__ runtime base
]


@pytest.mark.parametrize("n_calls", [1, 2, 5])
@pytest.mark.parametrize(
    ("op", "per_call"),
    [(op, counts) for _, op, counts in _ACCUMULATING_COUNTED_FLOAT_OPS],
    ids=[i for i, _, _ in _ACCUMULATING_COUNTED_FLOAT_OPS],
)
def test_repeated_counted_float_ops_accumulate_their_counts(
    thread_counter, op: Callable, per_call: dict[str, int], n_calls: int
):
    # --- act ---------------------------------------------
    for _ in range(n_calls):
        op()

    # --- assert ------------------------------------------
    for field, count in per_call.items():
        assert getattr(thread_counter, field) == n_calls * count
    assert thread_counter.total_count() == n_calls * sum(per_call.values())
