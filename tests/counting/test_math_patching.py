import math
import subprocess
import sys

import pytest

from counted_float import FlopCountingContext
from counted_float._core.counting import _math_patching
from counted_float._core.counting._counted_float import CountedFloat

PATCHED_FUNCTION_NAMES = sorted(_math_patching._PATCHES.keys())

# captured at import of this test module, i.e. with no counting context active anywhere
STDLIB_MATH_FUNCTIONS = {name: getattr(math, name) for name in PATCHED_FUNCTION_NAMES}


# =================================================================================================
#  Patch lifecycle - math module untouched outside contexts, patched inside
# =================================================================================================
def test_import_does_not_patch_math():
    # run in a fresh interpreter, so this test is independent of any context activity in this one
    code = (
        "import math; before = math.sqrt; import counted_float; "
        "assert math.sqrt is before, 'math.sqrt was patched at import time'"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603 -- fixed interpreter, literal code


@pytest.mark.parametrize("fname", PATCHED_FUNCTION_NAMES)
def test_math_module_patched_inside_context_only(fname):
    original = STDLIB_MATH_FUNCTIONS[fname]
    replacement = _math_patching._PATCHES[fname]

    # --- before any context ------------------------------
    assert getattr(math, fname) is original

    # --- inside (nested) contexts ------------------------
    with FlopCountingContext():
        assert getattr(math, fname) is replacement
        with FlopCountingContext():
            assert getattr(math, fname) is replacement
        # still patched after the inner context exits
        assert getattr(math, fname) is replacement

    # --- after all contexts have exited ------------------
    assert getattr(math, fname) is original


# =================================================================================================
#  Patched math functions - stdlib contract for plain floats
# =================================================================================================
@pytest.mark.parametrize(
    ("fname", "args"),
    [
        ("sqrt", (2.0,)),
        ("cbrt", (2.0,)),
        ("log", (2.0,)),
        ("log", (8.0, 2.0)),
        ("log2", (2.0,)),
        ("log10", (2.0,)),
        ("exp", (2.0,)),
        ("exp2", (2.0,)),
        ("pow", (2.0, 3.0)),
        ("pow", (2, 3)),
        ("sin", (2.0,)),
        ("cos", (2.0,)),
        ("tan", (2.0,)),
        ("asin", (0.5,)),
        ("acos", (0.5,)),
        ("atan", (0.5,)),
        ("atan2", (1.0, 2.0)),
        ("hypot", (3.0, 4.0)),
        ("expm1", (0.5,)),
        ("log1p", (0.5,)),
        ("fmod", (5.0, 3.0)),
        ("fabs", (-2.0,)),
        ("sinh", (0.5,)),
        ("cosh", (0.5,)),
        ("tanh", (0.5,)),
        ("asinh", (0.5,)),
        ("acosh", (2.0,)),
        ("atanh", (0.5,)),
    ],
)
def test_patched_math_functions_match_stdlib_for_plain_floats(global_counter, fname, args):
    # --- arrange -----------------------------------------
    patched = getattr(math, fname)  # fixture keeps a context active, so this is the replacement
    original = STDLIB_MATH_FUNCTIONS[fname]
    assert patched is not original

    # --- act ---------------------------------------------
    result = patched(*args)
    expected = original(*args)

    # --- assert ------------------------------------------
    assert result == expected
    assert type(result) is type(expected)
    assert not isinstance(result, CountedFloat)


def test_math_log_supports_two_arg_form(global_counter):
    # regression test: patched math.log used to raise TypeError for the 2-arg form
    # --- act ---------------------------------------------
    result = math.log(8, 2)

    # --- assert ------------------------------------------
    assert result == 3.0
    assert not isinstance(result, CountedFloat)


def test_math_pow_raises_domain_error_for_negative_base(global_counter):
    # regression test: patched math.pow used to return a complex number instead of raising
    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        math.pow(-8.0, 1 / 3)


def test_math_pow_returns_float_not_int(global_counter):
    # --- act ---------------------------------------------
    result = math.pow(2, 3)

    # --- assert ------------------------------------------
    assert result == 8.0
    assert type(result) is float


# =================================================================================================
#  Patched math functions - CountedFloat behavior of the log/pow code paths
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


def test_math_log_constant_float_base_folds_like_int(global_counter):
    # constants fold by value: a plain-float base is as precomputable as an int one, so a
    # compiled port emits log(x) * (1/log(base)) — LOG + MUL, not a runtime DIV
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act & assert ------------------------------------
    result = math.log(cf, 3.0)
    assert global_counter.total_count() == 2
    assert global_counter.LOG == 1
    assert global_counter.MUL == 1
    assert isinstance(result, CountedFloat)

    # special constant values fold all the way to the dedicated instruction
    global_counter.reset()
    result = math.log(cf, 2.0)
    assert global_counter.total_count() == 1
    assert global_counter.LOG2 == 1
    assert isinstance(result, CountedFloat)

    global_counter.reset()
    result = math.log(cf, 10.0)
    assert global_counter.total_count() == 1
    assert global_counter.LOG10 == 1
    assert isinstance(result, CountedFloat)


def test_math_log_counted_base_counts_runtime_division(global_counter):
    # a CountedFloat base is genuinely runtime: a port computes log(x)/log(base)
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act & assert ------------------------------------
    # plain x, counted base: LOG (of the base) + DIV
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


def test_math_log_one_arg_form_still_counts(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act ---------------------------------------------
    result = math.log(cf)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert global_counter.total_count() == 1
    assert global_counter.LOG == 1


def test_math_log_two_arg_form_plain_floats_count_nothing(global_counter):
    # --- act ---------------------------------------------
    result = math.log(8.0, 2.0)

    # --- assert ------------------------------------------
    assert global_counter.total_count() == 0
    assert not isinstance(result, CountedFloat)


def test_math_log_domain_error_counts_nothing(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(-8.0)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        math.log(cf, 2)
    assert global_counter.total_count() == 0


def test_math_pow_domain_error_counts_nothing(global_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(-8.0)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        math.pow(cf, 1 / 3)
    assert global_counter.total_count() == 0


@pytest.mark.parametrize(
    ("fname", "arg"),
    [
        ("sqrt", CountedFloat(-1.0)),  # domain: x >= 0
        ("log", CountedFloat(-1.0)),  # domain: x > 0  (single-arg form)
        ("log2", CountedFloat(-1.0)),  # domain: x > 0
        ("log10", CountedFloat(-1.0)),  # domain: x > 0
        ("exp", CountedFloat(710.0)),  # overflow (OverflowError)
        ("exp2", CountedFloat(2000.0)),  # overflow (OverflowError)
        ("sin", CountedFloat(math.inf)),  # sin/cos/tan raise on +/-inf
        ("cos", CountedFloat(math.inf)),
        ("tan", CountedFloat(math.inf)),
        ("expm1", CountedFloat(710.0)),  # overflow (OverflowError)
    ],
)
def test_single_arg_math_ops_error_counts_nothing(global_counter, fname, arg):
    # regression: these all counted BEFORE the underlying call and leaked a phantom flop when it
    # raised; the compute-first contract now leaves nothing counted (matching the log-base/pow paths)
    # --- act & assert ------------------------------------
    with pytest.raises((ValueError, OverflowError)):
        getattr(math, fname)(arg)
    assert global_counter.total_count() == 0


# =================================================================================================
#  Patched math functions - new higher-order ops (asin/acos/atan/atan2/hypot/expm1/log1p/fmod/fabs)
# =================================================================================================
@pytest.mark.parametrize(
    ("fname", "n_args", "flop_type_name"),
    [
        ("asin", 1, "ASIN"),
        ("acos", 1, "ACOS"),
        ("atan", 1, "ATAN"),
        ("atan2", 2, "ATAN2"),
        ("hypot", 2, "HYPOT"),
        ("expm1", 1, "EXPM1"),
        ("log1p", 1, "LOG1P"),
        ("fmod", 2, "FMOD"),
        ("fabs", 1, "ABS"),  # fabs reuses the existing ABS type, not a new one
    ],
)
def test_new_math_ops_count_and_are_contagious(global_counter, fname, n_args, flop_type_name):
    # --- arrange -----------------------------------------
    args = tuple(CountedFloat(0.5) for _ in range(n_args))

    # --- act ---------------------------------------------
    result = getattr(math, fname)(*args)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert getattr(global_counter, flop_type_name) == 1
    assert global_counter.total_count() == 1


@pytest.mark.parametrize("fname", ["atan2", "hypot", "fmod"])
def test_new_binary_math_ops_count_with_either_operand_counted(global_counter, fname):
    # counted (and contagious) when EITHER operand is a CountedFloat, like the existing binary ops
    # --- act ---------------------------------------------
    r_left = getattr(math, fname)(CountedFloat(3.0), 2.0)
    r_right = getattr(math, fname)(3.0, CountedFloat(2.0))

    # --- assert ------------------------------------------
    assert isinstance(r_left, CountedFloat)
    assert isinstance(r_right, CountedFloat)
    assert global_counter.total_count() == 2


@pytest.mark.parametrize(
    ("fname", "args"),
    [
        ("asin", (CountedFloat(2.0),)),  # domain: |x| <= 1
        ("acos", (CountedFloat(2.0),)),
        ("log1p", (CountedFloat(-2.0),)),  # domain: x > -1
        ("fmod", (CountedFloat(5.0), CountedFloat(0.0))),  # fmod by zero
    ],
)
def test_new_math_ops_domain_error_counts_nothing(global_counter, fname, args):
    # compute-first contract: a raised domain error leaves nothing counted
    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        getattr(math, fname)(*args)
    assert global_counter.total_count() == 0


# =================================================================================================
#  Patched math functions - hyperbolic ops (sinh/cosh/tanh/asinh/acosh/atanh)
# =================================================================================================
@pytest.mark.parametrize(
    ("fname", "arg", "flop_type_name"),
    [
        ("sinh", 0.5, "SINH"),
        ("cosh", 0.5, "COSH"),
        ("tanh", 0.5, "TANH"),
        ("asinh", 0.5, "ASINH"),
        ("acosh", 2.0, "ACOSH"),  # acosh domain: x >= 1
        ("atanh", 0.5, "ATANH"),  # atanh domain: |x| < 1
    ],
)
def test_hyperbolic_math_ops_count_and_are_contagious(global_counter, fname, arg, flop_type_name):
    # --- act ---------------------------------------------
    result = getattr(math, fname)(CountedFloat(arg))

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert getattr(global_counter, flop_type_name) == 1
    assert global_counter.total_count() == 1


@pytest.mark.parametrize(
    ("fname", "arg"),
    [
        ("acosh", CountedFloat(0.5)),  # domain: x >= 1
        ("atanh", CountedFloat(2.0)),  # domain: |x| < 1
        ("sinh", CountedFloat(1e6)),  # overflow
        ("cosh", CountedFloat(1e6)),  # overflow
    ],
)
def test_hyperbolic_math_ops_error_counts_nothing(global_counter, fname, arg):
    # compute-first contract: a domain/overflow error leaves nothing counted
    # --- act & assert ------------------------------------
    with pytest.raises((ValueError, OverflowError)):
        getattr(math, fname)(arg)
    assert global_counter.total_count() == 0


# =================================================================================================
#  Playing nice with third-party math patches
# =================================================================================================
def test_third_party_math_patches_are_delegated_through_and_restored():
    # a third party patches math.sqrt AFTER counted_float was imported; our patching must
    # delegate through that patch while active and restore it (not the stdlib) afterwards
    # --- arrange -----------------------------------------
    stdlib_sqrt = STDLIB_MATH_FUNCTIONS["sqrt"]
    third_party_calls = []

    def third_party_sqrt(x):
        third_party_calls.append(float(x))
        return stdlib_sqrt(x)

    math.sqrt = third_party_sqrt
    try:
        # --- act & assert --------------------------------
        with FlopCountingContext() as ctx:
            result = math.sqrt(CountedFloat(4.0))

        assert isinstance(result, CountedFloat)
        assert result == 2.0
        assert ctx.flop_counts().SQRT == 1
        assert third_party_calls == [4.0]  # our replacement delegated through the 3rd-party patch
        assert math.sqrt is third_party_sqrt  # ...and restored it, not the stdlib function
    finally:
        math.sqrt = stdlib_sqrt


# =================================================================================================
#  Behavior outside a counting context
# =================================================================================================
def test_math_functions_do_not_count_outside_context():
    # no context active here: math.* functions are the stdlib originals, so a CountedFloat input
    # produces a plain float and no counts (operator-based contagion is unaffected by this)
    # --- arrange -----------------------------------------
    cf = CountedFloat(4.0)

    # --- act ---------------------------------------------
    result = math.sqrt(cf)

    # --- assert ------------------------------------------
    assert result == 2.0
    assert not isinstance(result, CountedFloat)
