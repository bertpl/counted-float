import math

import pytest

from counted_float._core.counting._counted_float import (
    CountedFloat,
    original_math_cbrt,
    original_math_cos,
    original_math_exp,
    original_math_exp2,
    original_math_log,
    original_math_log2,
    original_math_log10,
    original_math_pow,
    original_math_sin,
    original_math_sqrt,
    original_math_tan,
)


# =================================================================================================
#  Patched math functions - stdlib contract for plain floats
# =================================================================================================
@pytest.mark.parametrize(
    "patched, original, args",
    [
        (math.sqrt, original_math_sqrt, (2.0,)),
        (math.cbrt, original_math_cbrt, (2.0,)),
        (math.log, original_math_log, (2.0,)),
        (math.log, original_math_log, (8.0, 2.0)),
        (math.log2, original_math_log2, (2.0,)),
        (math.log10, original_math_log10, (2.0,)),
        (math.exp, original_math_exp, (2.0,)),
        (math.exp2, original_math_exp2, (2.0,)),
        (math.pow, original_math_pow, (2.0, 3.0)),
        (math.pow, original_math_pow, (2, 3)),
        (math.sin, original_math_sin, (2.0,)),
        (math.cos, original_math_cos, (2.0,)),
        (math.tan, original_math_tan, (2.0,)),
    ],
)
def test_patched_math_functions_match_stdlib_for_plain_floats(patched, original, args):
    # --- act ---------------------------------------------
    result = patched(*args)
    expected = original(*args)

    # --- assert ------------------------------------------
    assert result == expected
    assert type(result) is type(expected)
    assert not isinstance(result, CountedFloat)


def test_math_log_supports_two_arg_form():
    # regression test: patched math.log used to raise TypeError for the 2-arg form
    # --- act ---------------------------------------------
    result = math.log(8, 2)

    # --- assert ------------------------------------------
    assert result == 3.0
    assert not isinstance(result, CountedFloat)


def test_math_pow_raises_domain_error_for_negative_base():
    # regression test: patched math.pow used to return a complex number instead of raising
    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):
        math.pow(-8.0, 1 / 3)


def test_math_pow_returns_float_not_int():
    # --- act ---------------------------------------------
    result = math.pow(2, 3)

    # --- assert ------------------------------------------
    assert result == 8.0
    assert type(result) is float


# =================================================================================================
#  Patched math functions - CountedFloat behavior of the fixed code paths
# =================================================================================================
def test_math_log_int_base_2_counts_log2(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act ---------------------------------------------
    result = math.log(cf, 2)

    # --- assert ------------------------------------------
    # count checked first: comparing a CountedFloat below counts a COMP itself
    assert global_counter.total_count() == 1
    assert global_counter.LOG2 == 1
    assert result == 3.0
    assert isinstance(result, CountedFloat)


def test_math_log_int_base_10_counts_log10(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(100.0)

    # --- act ---------------------------------------------
    result = math.log(cf, 10)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 1
    assert global_counter.LOG10 == 1
    assert result == 2.0
    assert isinstance(result, CountedFloat)


def test_math_log_other_int_base_counts_log_mul(global_counter):
    # a hardcoded int base folds to log(x) * (1/log(base)) in a compiled port
    # --- arrange -----------------------------------------
    cf = CountedFloat(27.0)

    # --- act ---------------------------------------------
    result = math.log(cf, 3)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 2
    assert global_counter.LOG == 1
    assert global_counter.MUL == 1
    assert result == pytest.approx(3.0)
    assert isinstance(result, CountedFloat)


def test_math_log_float_base_counts_per_counted_operand(global_counter):
    # a runtime (float) base means a compiled port computes log(x)/log(base)
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act & assert ------------------------------------
    # counted x, plain base: LOG + DIV (log of the untracked base is precomputable)
    result = math.log(cf, 2.0)
    assert global_counter.total_count() == 2
    assert global_counter.LOG == 1
    assert global_counter.DIV == 1
    assert isinstance(result, CountedFloat)

    # plain x, counted base: LOG + DIV
    global_counter.reset()
    result = math.log(16.0, CountedFloat(2.0))
    assert global_counter.total_count() == 2
    assert global_counter.LOG == 1
    assert global_counter.DIV == 1
    assert isinstance(result, CountedFloat)

    # both counted: 2 x LOG + DIV
    global_counter.reset()
    result = math.log(cf, CountedFloat(2.0))
    assert global_counter.total_count() == 3
    assert global_counter.LOG == 2
    assert global_counter.DIV == 1
    assert isinstance(result, CountedFloat)


def test_math_log_two_arg_form_plain_floats_count_nothing(global_counter):
    # --- act ---------------------------------------------
    result = math.log(8.0, 2.0)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 0
    assert not isinstance(result, CountedFloat)


def test_math_log_one_arg_form_still_counts(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act ---------------------------------------------
    result = math.log(cf)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert global_counter.total_count() == 1
    assert global_counter.LOG == 1


def test_math_log_domain_error_counts_nothing(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(-8.0)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):
        math.log(cf, 2)
    assert global_counter.total_count() == 0


def test_math_pow_domain_error_counts_nothing(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(-8.0)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):
        math.pow(cf, 1 / 3)
    assert global_counter.total_count() == 0
