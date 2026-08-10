import math
import operator
from collections.abc import Callable

import pytest

from counted_float._core.counting._counted_float import CountedFloat


# =================================================================================================
#  CountedFloat - min/max, and the folds that key on plain constants
# =================================================================================================
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


@pytest.mark.parametrize(
    ("case", "expected_counts"),
    [
        # --- folds: the compiled port emits nothing (rule 1 - identity-folds-are-sign-exact) ---
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
        # --- ... and a ±1.0 divisor folds the remainder's y*floor(x/y) multiply too ---
        (lambda cf: cf % 1.0, {"RND": 1, "SUB": 1}),
        (lambda cf: cf % 1, {"RND": 1, "SUB": 1}),  # int 1 compiles as 1.0
        (lambda cf: cf % -1.0, {"MINUS": 2, "RND": 1, "SUB": 1}),  # division step and multiply are both sign flips
        (lambda cf: divmod(cf, 1.0), {"RND": 1, "SUB": 1}),
        (lambda cf: divmod(cf, -1.0), {"MINUS": 2, "RND": 1, "SUB": 1}),
    ],
)
def test_counted_float_identity_folds(thread_counter, case, expected_counts: dict[str, int]):
    """The identity folds of rule 1 - identity-folds-are-sign-exact, and the near-misses that must not fold."""
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
        (lambda cf: cf % CountedFloat(1.0), {"DIV": 1, "RND": 1, "MUL": 1, "SUB": 1}),
        (lambda cf: divmod(cf, CountedFloat(-1.0)), {"DIV": 1, "RND": 1, "MUL": 1, "SUB": 1}),
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


# =================================================================================================
#  CountedFloat - pow dispatch, zero division, and reflected deferral
# =================================================================================================
def test_counted_float_counts_math_pow_forms(thread_counter):
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


def test_counted_float_counted_zero_exponent_and_one_base_stay_runtime(thread_counter):
    """A CountedFloat operand is the opt-in: the absorbing values fold only as plain constants."""
    # --- act ---------------------------------------------
    result_exponent = CountedFloat(1.23456) ** CountedFloat(0.0)
    result_base = CountedFloat(1.0) ** CountedFloat(2.5)

    # --- assert ------------------------------------------
    assert isinstance(result_exponent, CountedFloat)
    assert isinstance(result_base, CountedFloat)
    assert thread_counter.POW == 2
    assert thread_counter.total_count() == 2


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
