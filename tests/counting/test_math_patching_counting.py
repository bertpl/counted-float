import math

import pytest

from counted_float._core.counting import _math_patching
from counted_float._core.counting._counted_float import CountedFloat

from .conftest import STDLIB_MATH_FUNCTIONS


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
        ("degrees", (2.0,)),
        ("radians", (90.0,)),
        ("dist", ((1.0, 2.0), (4.0, 6.0))),
        ("prod", ([2.0, 3.0, 4.0],)),
        ("prod", ([2, 3, 4],)),  # int-exactness of the original is preserved
        ("fsum", ([0.1] * 10,)),
        ("copysign", (3.0, -2.0)),
        ("hypot", (1.0, 2.0, 2.0)),
        ("hypot", (-3.0,)),
        # plain-float delegation paths for the special functions (their CountedFloat counting
        # paths are exercised separately in test_new_math_ops_count_and_are_contagious)
        ("gamma", (2.0,)),
        ("lgamma", (2.0,)),
        ("erf", (0.5,)),
        ("erfc", (0.5,)),
        ("remainder", (5.0, 3.0)),
    ],
)
def test_patched_math_functions_match_stdlib_for_plain_floats(thread_counter, fname, args):
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


def test_math_log_supports_two_arg_form(thread_counter):
    # regression test: patched math.log used to raise TypeError for the 2-arg form
    # --- act ---------------------------------------------
    result = math.log(8, 2)

    # --- assert ------------------------------------------
    assert result == 3.0
    assert not isinstance(result, CountedFloat)


def test_math_pow_raises_domain_error_for_negative_base(thread_counter):
    # regression test: patched math.pow used to return a complex number instead of raising
    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        math.pow(-8.0, 1 / 3)


def test_math_pow_returns_float_not_int(thread_counter):
    # --- act ---------------------------------------------
    result = math.pow(2, 3)

    # --- assert ------------------------------------------
    assert result == 8.0
    assert type(result) is float


# =================================================================================================
#  Patched math functions - CountedFloat behavior of the log/pow code paths
# =================================================================================================
def test_math_log_int_base_2_counts_log2(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act ---------------------------------------------
    result = math.log(cf, 2)

    # --- assert ------------------------------------------
    # count checked first: comparing a CountedFloat below counts a COMP itself
    assert thread_counter.total_count() == 1
    assert thread_counter.LOG2 == 1
    assert result == 3.0
    assert isinstance(result, CountedFloat)


def test_math_log_int_base_10_counts_log10(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(100.0)

    # --- act ---------------------------------------------
    result = math.log(cf, 10)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.LOG10 == 1
    assert result == 2.0
    assert isinstance(result, CountedFloat)


def test_math_log_other_int_base_counts_log_mul(thread_counter):
    # a hardcoded int base folds to log(x) * (1/log(base)) in a compiled port
    # --- arrange -----------------------------------------
    cf = CountedFloat(27.0)

    # --- act ---------------------------------------------
    result = math.log(cf, 3)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 2
    assert thread_counter.LOG == 1
    assert thread_counter.MUL == 1
    assert result == pytest.approx(3.0)
    assert isinstance(result, CountedFloat)


def test_math_log_constant_float_base_folds_like_int(thread_counter):
    # constants fold by value: a plain-float base is as precomputable as an int one, so a
    # compiled port emits log(x) * (1/log(base)) — LOG + MUL, not a runtime DIV
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act & assert ------------------------------------
    result = math.log(cf, 3.0)
    assert thread_counter.total_count() == 2
    assert thread_counter.LOG == 1
    assert thread_counter.MUL == 1
    assert isinstance(result, CountedFloat)

    # special constant values fold all the way to the dedicated instruction
    thread_counter.reset()
    result = math.log(cf, 2.0)
    assert thread_counter.total_count() == 1
    assert thread_counter.LOG2 == 1
    assert isinstance(result, CountedFloat)

    thread_counter.reset()
    result = math.log(cf, 10.0)
    assert thread_counter.total_count() == 1
    assert thread_counter.LOG10 == 1
    assert isinstance(result, CountedFloat)


@pytest.mark.parametrize(
    ("base", "expected_counts"),
    [
        pytest.param(
            math.e,
            {"LOG": 1},
            marks=pytest.mark.skipif(
                math.log(math.e) != 1.0,
                reason="the fold keys on the runtime value: this libm does not give log(e) == 1.0",
            ),
            id="unit-multiplier-folds-away",
        ),
        pytest.param(
            1.0 / math.e,
            {"LOG": 1, "MINUS": 1},
            marks=pytest.mark.skipif(
                math.log(1.0 / math.e) != -1.0,
                reason="the fold keys on the runtime value: this libm does not give log(1/e) == -1.0",
            ),
            id="negative-unit-multiplier-is-a-sign-flip",
        ),
    ],
)
def test_math_log_constant_base_with_unit_reciprocal_folds_multiply(thread_counter, base, expected_counts):
    # the port's multiplier C = 1/log(base) is itself a compile-time constant, so the identity
    # folds apply to it: C = 1.0 drops the multiply, C = -1.0 is a bare sign flip
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act ---------------------------------------------
    result = math.log(cf, base)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert thread_counter.total_count() == sum(expected_counts.values())
    for field, expected in expected_counts.items():
        assert getattr(thread_counter, field) == expected


def test_math_log_counted_base_counts_runtime_division(thread_counter):
    # a CountedFloat base is genuinely runtime: a port computes log(x)/log(base)
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act & assert ------------------------------------
    # plain x, counted base: LOG (of the base) + DIV
    result = math.log(16.0, CountedFloat(2.0))
    assert thread_counter.total_count() == 2
    assert thread_counter.LOG == 1
    assert thread_counter.DIV == 1
    assert isinstance(result, CountedFloat)

    # both counted: 2 x LOG + DIV
    thread_counter.reset()
    result = math.log(cf, CountedFloat(2.0))
    assert thread_counter.total_count() == 3
    assert thread_counter.LOG == 2
    assert thread_counter.DIV == 1
    assert isinstance(result, CountedFloat)


def test_math_log_one_arg_form_still_counts(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(8.0)

    # --- act ---------------------------------------------
    result = math.log(cf)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert thread_counter.total_count() == 1
    assert thread_counter.LOG == 1


def test_math_log_two_arg_form_plain_floats_count_nothing(thread_counter):
    # --- act ---------------------------------------------
    result = math.log(8.0, 2.0)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 0
    assert not isinstance(result, CountedFloat)


def test_math_log_domain_error_counts_nothing(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(-8.0)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        math.log(cf, 2)
    assert thread_counter.total_count() == 0


def test_math_pow_domain_error_counts_nothing(thread_counter):
    # --- arrange -----------------------------------------
    cf = CountedFloat(-8.0)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        math.pow(cf, 1 / 3)
    assert thread_counter.total_count() == 0


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
def test_single_arg_math_ops_error_counts_nothing(thread_counter, fname, arg):
    # regression: these all counted BEFORE the underlying call and leaked a phantom flop when it
    # raised; the compute-first contract now leaves nothing counted (matching the log-base/pow paths)
    # --- act & assert ------------------------------------
    with pytest.raises((ValueError, OverflowError)):
        getattr(math, fname)(arg)
    assert thread_counter.total_count() == 0


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
        ("gamma", 1, "GAMMA"),
        ("lgamma", 1, "LGAMMA"),
        ("erf", 1, "ERF"),
        ("erfc", 1, "ERFC"),
        ("remainder", 2, "REMAINDER"),
    ],
)
def test_new_math_ops_count_and_are_contagious(thread_counter, fname, n_args, flop_type_name):
    # --- arrange -----------------------------------------
    args = tuple(CountedFloat(0.5) for _ in range(n_args))

    # --- act ---------------------------------------------
    result = getattr(math, fname)(*args)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert getattr(thread_counter, flop_type_name) == 1
    assert thread_counter.total_count() == 1


@pytest.mark.parametrize("fname", ["atan2", "hypot", "fmod", "remainder"])
def test_new_binary_math_ops_count_with_either_operand_counted(thread_counter, fname):
    # counted (and contagious) when EITHER operand is a CountedFloat, like the existing binary ops
    # --- act ---------------------------------------------
    r_left = getattr(math, fname)(CountedFloat(3.0), 2.0)
    r_right = getattr(math, fname)(3.0, CountedFloat(2.0))

    # --- assert ------------------------------------------
    assert isinstance(r_left, CountedFloat)
    assert isinstance(r_right, CountedFloat)
    assert thread_counter.total_count() == 2


@pytest.mark.parametrize(
    ("fname", "args"),
    [
        ("asin", (CountedFloat(2.0),)),  # domain: |x| <= 1
        ("acos", (CountedFloat(2.0),)),
        ("log1p", (CountedFloat(-2.0),)),  # domain: x > -1
        ("fmod", (CountedFloat(5.0), CountedFloat(0.0))),  # fmod by zero
    ],
)
def test_new_math_ops_domain_error_counts_nothing(thread_counter, fname, args):
    # compute-first contract: a raised domain error leaves nothing counted
    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        getattr(math, fname)(*args)
    assert thread_counter.total_count() == 0


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
def test_hyperbolic_math_ops_count_and_are_contagious(thread_counter, fname, arg, flop_type_name):
    # --- act ---------------------------------------------
    result = getattr(math, fname)(CountedFloat(arg))

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert getattr(thread_counter, flop_type_name) == 1
    assert thread_counter.total_count() == 1


@pytest.mark.parametrize(
    ("fname", "arg"),
    [
        ("acosh", CountedFloat(0.5)),  # domain: x >= 1
        ("atanh", CountedFloat(2.0)),  # domain: |x| < 1
        ("sinh", CountedFloat(1e6)),  # overflow
        ("cosh", CountedFloat(1e6)),  # overflow
    ],
)
def test_hyperbolic_math_ops_error_counts_nothing(thread_counter, fname, arg):
    # compute-first contract: a domain/overflow error leaves nothing counted
    # --- act & assert ------------------------------------
    with pytest.raises((ValueError, OverflowError)):
        getattr(math, fname)(arg)
    assert thread_counter.total_count() == 0


# =================================================================================================
#  Patched math functions - decomposed ops (degrees/radians/dist/prod/fsum/copysign/hypot arity)
# =================================================================================================
@pytest.mark.parametrize("fname", ["degrees", "radians"])
def test_degrees_radians_count_one_mul(thread_counter, fname):
    # --- act ---------------------------------------------
    result = getattr(math, fname)(CountedFloat(1.0))

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert thread_counter.MUL == 1
    assert thread_counter.total_count() == 1


@pytest.mark.parametrize("n_dims", [1, 2, 3, 5])
def test_dist_counts_the_arity_scaled_types(thread_counter, n_dims):
    # --- arrange -----------------------------------------
    p = [CountedFloat(float(i)) for i in range(n_dims)]
    q = [float(2 * i + 1) for i in range(n_dims)]

    # --- act ---------------------------------------------
    result = math.dist(p, q)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    if n_dims == 1:
        # one dimension takes the same single-coordinate shortcut as 1-argument hypot: the call
        # computes |p0 - q0|, so the port pays the subtract and the fabs, not the 2-D base
        assert thread_counter.SUB == 1
        assert thread_counter.ABS == 1
        assert thread_counter.total_count() == 2
    else:
        assert thread_counter.DIST == 1
        assert max(0, n_dims - 2) == thread_counter.DIST_XARG
        assert thread_counter.total_count() == 1 + max(0, n_dims - 2)


def test_dist_accepts_iterator_inputs_and_mismatched_lengths_raise(thread_counter):
    # --- act / assert ------------------------------------
    result = math.dist(iter([CountedFloat(0.0), CountedFloat(0.0)]), iter([3.0, 4.0]))
    assert float(result) == 5.0
    assert isinstance(result, CountedFloat)

    with pytest.raises(ValueError):  # noqa: PT011 -- stdlib wording ("both points must have the same dimension")
        math.dist([CountedFloat(1.0)], [1.0, 2.0])
    assert thread_counter.DIST == 1  # only the successful call above counted anything


def test_dist_counts_when_only_q_holds_a_counted_float(thread_counter):
    # the contagion scan must cover BOTH point tuples: a CountedFloat present solely in q (with p
    # all plain floats) is still a runtime input and still counts DIST -- a scan that only inspects
    # p would miss it and hand back an uncounted plain float
    # --- act ---------------------------------------------
    result = math.dist([1.0, 2.0], [CountedFloat(4.0), CountedFloat(6.0)])

    # --- assert ------------------------------------------
    assert float(result) == 5.0
    assert isinstance(result, CountedFloat)
    assert thread_counter.DIST == 1
    assert thread_counter.total_count() == 1


@pytest.mark.parametrize("n_values", [1, 2, 4])
def test_prod_counts_the_multiply_chain(thread_counter, n_values):
    # --- arrange -----------------------------------------
    values = [CountedFloat(float(i + 2)) for i in range(n_values)]

    # --- act ---------------------------------------------
    result = math.prod(values)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert float(result) == math.prod(float(v) for v in values)
    assert n_values - 1 == thread_counter.MUL, "the identity start folds away: n-1 multiplies"
    assert thread_counter.total_count() == n_values - 1


def test_prod_with_an_explicit_start_counts_its_multiply(thread_counter):
    # --- act ---------------------------------------------
    result = math.prod([CountedFloat(2.0), CountedFloat(3.0)], start=CountedFloat(5.0))

    # --- assert ------------------------------------------
    assert float(result) == 30.0
    assert isinstance(result, CountedFloat)
    assert thread_counter.MUL == 2  # start*v1, then *v2


def test_prod_with_a_plain_nonidentity_start_is_not_folded_away(thread_counter):
    # a plain start of 2.0 is NOT the multiplicative identity: it opens the chain and its multiply
    # is counted, exactly as writing the chain out would. Only an identity start (plain 1) folds
    # away -- folding a non-identity start would drop a MUL and change the product itself
    # --- act ---------------------------------------------
    result = math.prod([CountedFloat(3.0), CountedFloat(4.0)], start=2.0)

    # --- assert ------------------------------------------
    assert float(result) == 24.0  # 2.0 * 3.0 * 4.0, not the folded-start 3.0 * 4.0 == 12.0
    assert isinstance(result, CountedFloat)
    assert thread_counter.MUL == 2  # 2.0*v1, then *v2
    assert thread_counter.total_count() == 2


def test_prod_without_counted_values_keeps_stdlib_behavior(thread_counter):
    # --- act / assert ------------------------------------
    result = math.prod([2, 3, 4])
    assert result == 24
    assert isinstance(result, int)  # int-exactness of the original is preserved
    assert thread_counter.total_count() == 0


def test_prod_without_counted_values_forwards_a_non_default_start(thread_counter):
    # the all-plain path delegates to the original; it must forward `start`, not drop it
    # --- act / assert ------------------------------------
    result = math.prod([2, 3, 4], start=10)
    assert result == 240  # 10 * 2 * 3 * 4, not the start-dropped 24
    assert thread_counter.total_count() == 0


@pytest.mark.parametrize("n_values", [1, 2, 5])
def test_fsum_counts_the_addition_chain(thread_counter, n_values):
    # --- arrange -----------------------------------------
    values = [CountedFloat(0.1)] * n_values

    # --- act ---------------------------------------------
    result = math.fsum(values)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert n_values - 1 == thread_counter.ADD
    assert thread_counter.total_count() == n_values - 1


def test_fsum_keeps_its_exactness(thread_counter):
    # the whole point of fsum: 0.1 summed ten times is exactly 1.0 (naive addition is not)
    # --- act ---------------------------------------------
    result = math.fsum([CountedFloat(0.1)] * 10)

    # --- assert ------------------------------------------
    assert float(result) == 1.0


def test_copysign_counts_its_own_flop_type(thread_counter):
    # --- act ---------------------------------------------
    r_left = math.copysign(CountedFloat(3.0), -2.0)
    r_right = math.copysign(3.0, CountedFloat(-2.0))

    # --- assert ------------------------------------------
    assert float(r_left) == float(r_right) == -3.0
    assert isinstance(r_left, CountedFloat)
    assert isinstance(r_right, CountedFloat)
    assert thread_counter.COPYSIGN == 2
    assert thread_counter.total_count() == 2


@pytest.mark.parametrize(
    ("n_args", "expected"),
    [
        (1, {"ABS": 1}),  # |x|: a port emits fabs
        (2, {"HYPOT": 1}),  # the libm hypot(x, y) call, as benchmarked
        (3, {"HYPOT": 1, "HYPOT_XARG": 1}),  # base cost + measured per-extra-coordinate slope
        (5, {"HYPOT": 1, "HYPOT_XARG": 3}),
    ],
)
def test_hypot_counts_per_arity(thread_counter, n_args, expected):
    # --- arrange -----------------------------------------
    args = tuple(CountedFloat(1.0) for _ in range(n_args))

    # --- act ---------------------------------------------
    result = math.hypot(*args)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    for flop_type_name, count in expected.items():
        assert getattr(thread_counter, flop_type_name) == count
    assert thread_counter.total_count() == sum(expected.values())


# =================================================================================================
#  Patched math functions - sumprod (unboxed delegation, arity-scaled counting)
# =================================================================================================
needs_sumprod = pytest.mark.skipif(not hasattr(math, "sumprod"), reason="math.sumprod exists from Python 3.12")


@needs_sumprod
@pytest.mark.parametrize("counted_side", ["p", "q"])
def test_sumprod_computes_the_extended_precision_result_for_counted_inputs(thread_counter, counted_side):
    # --- arrange -----------------------------------------
    # a cancellation case only the compensated exact-float path gets right: naive accumulation
    # absorbs the 1.0 into 1e100 and returns 0.0 -- which is exactly what an unboxing failure
    # (rerouting to the generic object path) would produce here
    values = [1e100, 1.0, -1e100]
    ones = [1.0, 1.0, 1.0]
    p = [CountedFloat(v) for v in values] if counted_side == "p" else values
    q = [CountedFloat(v) for v in ones] if counted_side == "q" else ones

    # --- act ---------------------------------------------
    result = math.sumprod(p, q)

    # --- assert ------------------------------------------
    assert float(result) == 1.0
    assert isinstance(result, CountedFloat)


@needs_sumprod
@pytest.mark.parametrize(("n_elements", "expected_xelem"), [(1, 0), (2, 0), (3, 1), (8, 6)])
def test_sumprod_counts_the_arity_scaled_types(thread_counter, n_elements, expected_xelem):
    # --- arrange -----------------------------------------
    p = [CountedFloat(float(i + 1)) for i in range(n_elements)]
    q = [float(2 * i + 1) for i in range(n_elements)]

    # --- act ---------------------------------------------
    result = math.sumprod(p, q)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert thread_counter.SUMPROD == 1
    assert expected_xelem == thread_counter.SUMPROD_XELEM
    assert thread_counter.total_count() == 1 + expected_xelem


@needs_sumprod
def test_sumprod_accepts_one_shot_iterators_and_mismatched_lengths_raise(thread_counter):
    # --- act / assert ------------------------------------
    result = math.sumprod((CountedFloat(v) for v in (1.0, 2.0)), (v for v in (3.0, 4.0)))
    assert float(result) == 11.0
    assert isinstance(result, CountedFloat)

    with pytest.raises(ValueError):  # noqa: PT011 -- stdlib wording ("inputs are not the same length")
        math.sumprod([CountedFloat(1.0)], [1.0, 2.0])
    assert thread_counter.SUMPROD == 1  # only the successful call above counted anything


@needs_sumprod
def test_sumprod_without_counted_values_keeps_stdlib_behavior(thread_counter):
    # --- act ---------------------------------------------
    result = math.sumprod([2, 3], [4, 5])

    # --- assert ------------------------------------------
    assert result == 23
    assert isinstance(result, int)  # int-exactness of the original is preserved
    assert thread_counter.total_count() == 0


# =================================================================================================
#  Patched math functions - fused multiply-add
# =================================================================================================
requires_fma = pytest.mark.skipif(not hasattr(math, "fma"), reason="math.fma requires Python 3.13+")


def test_math_fma_registered_only_where_available():
    """math.fma is patched exactly on the interpreters that have it, and never elsewhere."""
    # --- act & assert ------------------------------------
    assert ("fma" in _math_patching._PATCHES) == hasattr(math, "fma")


@requires_fma
@pytest.mark.parametrize(
    ("x", "y", "z"),
    [
        (CountedFloat(2.0), CountedFloat(3.0), CountedFloat(4.0)),
        (CountedFloat(2.0), 3.0, 4.0),
        (2.0, CountedFloat(3.0), 4.0),
        (CountedFloat(2.0), CountedFloat(3.0), 4.0),
        (2, CountedFloat(3.0), 4),
    ],
    ids=["all_runtime", "constant_y_and_z", "constant_x", "constant_z", "int_constants"],
)
def test_math_fma_counts_one_fma(thread_counter, x: float, y: float, z: float):
    """One fused instruction whenever a runtime multiplicand is involved; constants add no cost of their own."""
    # --- act ---------------------------------------------
    result = math.fma(x, y, z)

    # --- assert ------------------------------------------
    # count checked first: comparing a CountedFloat below counts a COMP itself
    assert thread_counter.total_count() == 1
    assert thread_counter.FMA == 1
    assert result == 10.0
    assert isinstance(result, CountedFloat)


@requires_fma
def test_math_fma_with_constant_multiplicands_counts_add(thread_counter):
    """Two constant multiplicands fold to one constant, leaving a compiled port with a bare add."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(4.0)

    # --- act ---------------------------------------------
    result = math.fma(2.0, 3.0, cf)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 1
    assert thread_counter.ADD == 1
    assert thread_counter.FMA == 0
    assert result == 10.0
    assert isinstance(result, CountedFloat)


@requires_fma
def test_math_fma_without_counted_operands_counts_nothing(thread_counter):
    """Every operand constant: the expression folds entirely and contagion does not start."""
    # --- act ---------------------------------------------
    result = math.fma(2.0, 3.0, 4.0)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 0
    assert result == 10.0
    assert type(result) is float


@requires_fma
def test_math_fma_domain_error_counts_nothing(thread_counter):
    """The stdlib's error surfaces before anything is counted."""
    # --- arrange -----------------------------------------
    cf = CountedFloat(1.0)

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError):  # noqa: PT011 -- domain-error message wording varies across CPython versions
        math.fma(math.inf, 0.0, cf)

    assert thread_counter.total_count() == 0


# =================================================================================================
#  Patched math functions - the CountedFloat return path carries the real value
# =================================================================================================
@pytest.mark.parametrize(
    ("fname", "args"),
    [
        ("sqrt", (2.0,)),
        ("cbrt", (2.0,)),
        ("log", (2.0,)),
        ("log2", (8.0,)),
        ("log10", (1000.0,)),
        ("exp", (2.0,)),
        ("exp2", (3.0,)),
        ("pow", (2.0, 3.0)),
        ("sin", (0.5,)),
        ("cos", (0.5,)),
        ("tan", (0.5,)),
        ("asin", (0.5,)),
        ("acos", (0.5,)),
        ("atan", (0.5,)),
        ("atan2", (1.0, 2.0)),
        ("hypot", (3.0, 4.0)),
        ("expm1", (0.5,)),
        ("log1p", (0.5,)),
        ("fmod", (5.0, 3.0)),
        ("remainder", (5.0, 3.0)),
        ("fabs", (-2.0,)),
        ("sinh", (0.5,)),
        ("cosh", (0.5,)),
        ("tanh", (0.5,)),
        ("asinh", (0.5,)),
        ("acosh", (2.0,)),
        ("atanh", (0.5,)),
        ("gamma", (2.5,)),
        ("lgamma", (2.5,)),
        ("erf", (0.5,)),
        ("erfc", (0.5,)),
        ("degrees", (2.0,)),
        ("radians", (90.0,)),
    ],
)
def test_patched_math_functions_carry_the_real_value_for_counted_floats(thread_counter, fname, args):
    # the counted-input twin of test_patched_math_functions_match_stdlib_for_plain_floats: on the
    # CountedFloat path the result is rewrapped via float.__new__(CountedFloat, result), and the
    # count-focused tests only assert the count and the type -- never the value.  Dropping that
    # result argument (returning a bare 0.0) passes every one of them, so the value is pinned here.
    # --- arrange -----------------------------------------
    original = STDLIB_MATH_FUNCTIONS[fname]
    counted_args = tuple(CountedFloat(a) for a in args)

    # --- act ---------------------------------------------
    result = getattr(math, fname)(*counted_args)

    # --- assert ------------------------------------------
    assert isinstance(result, CountedFloat)
    assert float(result) == original(*args)  # patched wraps the original's own result -> bit-identical


# =================================================================================================
#  Patched math functions - counts accumulate across repeated calls
# =================================================================================================
# Each op is invoked n_calls times from a fresh counter, asserting the count reaches n_calls x the
# per-call amount.  n_calls == 1 pins the single-shot count; n_calls in (2, 5) forces the accumulating
# form -- a single-shot test cannot tell `field += 1` from `field = 1` (both leave the field at 1).
_ACCUMULATING_MATH_OPS = [
    ("sqrt", lambda: math.sqrt(CountedFloat(2.0)), {"SQRT": 1}),
    ("cbrt", lambda: math.cbrt(CountedFloat(2.0)), {"CBRT": 1}),
    ("log", lambda: math.log(CountedFloat(2.0)), {"LOG": 1}),
    ("log2", lambda: math.log2(CountedFloat(2.0)), {"LOG2": 1}),
    ("log10", lambda: math.log10(CountedFloat(2.0)), {"LOG10": 1}),
    ("log_int_base", lambda: math.log(CountedFloat(27.0), 3), {"LOG": 1, "MUL": 1}),
    ("log_counted_base", lambda: math.log(16.0, CountedFloat(2.0)), {"LOG": 1, "DIV": 1}),
    ("log_const_base_2", lambda: math.log(CountedFloat(8.0), 2), {"LOG2": 1}),  # base 2 folds to LOG2
    ("log_const_base_10", lambda: math.log(CountedFloat(1000.0), 10), {"LOG10": 1}),  # base 10 folds to LOG10
    ("exp", lambda: math.exp(CountedFloat(0.5)), {"EXP": 1}),
    ("exp2", lambda: math.exp2(CountedFloat(0.5)), {"EXP2": 1}),
    ("sin", lambda: math.sin(CountedFloat(0.5)), {"SIN": 1}),
    ("asin", lambda: math.asin(CountedFloat(0.5)), {"ASIN": 1}),
    ("acos", lambda: math.acos(CountedFloat(0.5)), {"ACOS": 1}),
    ("atan", lambda: math.atan(CountedFloat(0.5)), {"ATAN": 1}),
    ("atan2", lambda: math.atan2(CountedFloat(1.0), CountedFloat(2.0)), {"ATAN2": 1}),
    ("expm1", lambda: math.expm1(CountedFloat(0.5)), {"EXPM1": 1}),
    ("log1p", lambda: math.log1p(CountedFloat(0.5)), {"LOG1P": 1}),
    ("sinh", lambda: math.sinh(CountedFloat(0.5)), {"SINH": 1}),
    ("cosh", lambda: math.cosh(CountedFloat(0.5)), {"COSH": 1}),
    ("tanh", lambda: math.tanh(CountedFloat(0.5)), {"TANH": 1}),
    ("asinh", lambda: math.asinh(CountedFloat(0.5)), {"ASINH": 1}),
    ("acosh", lambda: math.acosh(CountedFloat(2.0)), {"ACOSH": 1}),
    ("atanh", lambda: math.atanh(CountedFloat(0.5)), {"ATANH": 1}),
    ("gamma", lambda: math.gamma(CountedFloat(2.5)), {"GAMMA": 1}),
    ("lgamma", lambda: math.lgamma(CountedFloat(2.5)), {"LGAMMA": 1}),
    ("erf", lambda: math.erf(CountedFloat(0.5)), {"ERF": 1}),
    ("erfc", lambda: math.erfc(CountedFloat(0.5)), {"ERFC": 1}),
    ("fabs", lambda: math.fabs(CountedFloat(-2.0)), {"ABS": 1}),
    ("fmod", lambda: math.fmod(CountedFloat(5.0), CountedFloat(3.0)), {"FMOD": 1}),
    ("remainder", lambda: math.remainder(CountedFloat(5.0), CountedFloat(3.0)), {"REMAINDER": 1}),
    ("isnan", lambda: math.isnan(CountedFloat(2.0)), {"COMP": 1}),
    ("isinf", lambda: math.isinf(CountedFloat(2.0)), {"ABS": 1, "COMP": 1}),
    ("isfinite", lambda: math.isfinite(CountedFloat(2.0)), {"ABS": 1, "COMP": 1}),
    ("isclose", lambda: math.isclose(CountedFloat(2.0), 2.5), {"SUB": 1, "ABS": 3, "MUL": 1, "COMP": 3}),
    ("hypot_abs", lambda: math.hypot(CountedFloat(-3.0)), {"ABS": 1}),
    ("hypot2", lambda: math.hypot(CountedFloat(3.0), CountedFloat(4.0)), {"HYPOT": 1}),
    (
        "hypot3",
        lambda: math.hypot(CountedFloat(1.0), CountedFloat(2.0), CountedFloat(2.0)),
        {"HYPOT": 1, "HYPOT_XARG": 1},
    ),
    (
        "dist3",
        lambda: math.dist([CountedFloat(0.0), CountedFloat(0.0), CountedFloat(0.0)], [1.0, 2.0, 2.0]),
        {"DIST": 1, "DIST_XARG": 1},
    ),
    ("fsum", lambda: math.fsum([CountedFloat(0.1)] * 3), {"ADD": 2}),
    ("degrees", lambda: math.degrees(CountedFloat(1.0)), {"MUL": 1}),
    ("radians", lambda: math.radians(CountedFloat(1.0)), {"MUL": 1}),
]


@pytest.mark.parametrize("n_calls", [1, 2, 5])
@pytest.mark.parametrize(
    ("op", "per_call"),
    [(op, counts) for _, op, counts in _ACCUMULATING_MATH_OPS],
    ids=[i for i, _, _ in _ACCUMULATING_MATH_OPS],
)
def test_repeated_math_ops_accumulate_their_counts(thread_counter, op, per_call: dict[str, int], n_calls: int):
    # --- act ---------------------------------------------
    for _ in range(n_calls):
        op()

    # --- assert ------------------------------------------
    for field, count in per_call.items():
        assert getattr(thread_counter, field) == n_calls * count
    assert thread_counter.total_count() == n_calls * sum(per_call.values())


@requires_fma
@pytest.mark.parametrize("n_calls", [1, 2, 5])
def test_repeated_fma_accumulates_its_count(thread_counter, n_calls: int):
    # --- act ---------------------------------------------
    for _ in range(n_calls):
        math.fma(CountedFloat(2.0), CountedFloat(3.0), CountedFloat(4.0))

    # --- assert ------------------------------------------
    assert n_calls == thread_counter.FMA
    assert thread_counter.total_count() == n_calls


@requires_fma
@pytest.mark.parametrize("n_calls", [1, 2, 5])
def test_repeated_fma_with_constant_multiplicands_accumulates_add(thread_counter, n_calls: int):
    # two constant multiplicands fold to one constant, leaving a bare ADD; a distinct counting site
    # from the fused FMA above
    # --- act ---------------------------------------------
    for _ in range(n_calls):
        math.fma(2.0, 3.0, CountedFloat(4.0))

    # --- assert ------------------------------------------
    assert n_calls == thread_counter.ADD
    assert thread_counter.total_count() == n_calls


@needs_sumprod
@pytest.mark.parametrize("n_calls", [1, 2, 5])
def test_repeated_sumprod_accumulates_its_counts(thread_counter, n_calls: int):
    # 3 elements -> SUMPROD + 1 SUMPROD_XELEM per call
    # --- act ---------------------------------------------
    for _ in range(n_calls):
        math.sumprod([CountedFloat(1.0), CountedFloat(2.0), CountedFloat(3.0)], [1.0, 1.0, 1.0])

    # --- assert ------------------------------------------
    assert n_calls == thread_counter.SUMPROD
    assert n_calls == thread_counter.SUMPROD_XELEM
    assert thread_counter.total_count() == 2 * n_calls


@pytest.mark.parametrize("value", [1.5, 0.0, math.inf, -math.inf, math.nan], ids=repr)
def test_math_isnan_counts_one_comp(thread_counter, value):
    # --- act ---------------------------------------------
    result = math.isnan(CountedFloat(value))

    # --- assert ------------------------------------------
    assert result is math.isnan(value)
    assert type(result) is bool
    assert thread_counter.COMP == 1  # the self-compare a port emits; charged on every regime
    assert thread_counter.total_count() == 1


@pytest.mark.parametrize("classifier_name", ["isinf", "isfinite"])
@pytest.mark.parametrize("value", [1.5, math.inf, math.nan], ids=repr)
def test_math_isinf_and_isfinite_count_abs_and_comp(thread_counter, classifier_name, value):
    # --- arrange -----------------------------------------
    classifier = getattr(math, classifier_name)  # resolved inside the context, where the patch is installed

    # --- act ---------------------------------------------
    result = classifier(CountedFloat(value))

    # --- assert ------------------------------------------
    assert result is classifier(value)
    assert thread_counter.ABS == 1  # the FP-canonical fabs-then-compare against infinity
    assert thread_counter.COMP == 1
    assert thread_counter.total_count() == 2


@pytest.mark.parametrize(
    "arguments",
    [
        (CountedFloat(2.0), 2.5),
        (2.0, CountedFloat(2.0)),
        (CountedFloat(1e300), CountedFloat(-1e300)),
        (CountedFloat(math.nan), 1.0),
        (CountedFloat(math.inf), 1.0),  # the infinity guard is a regime fast path: same price
        (CountedFloat(2.0), 2.0),  # the equality guard likewise
    ],
    ids=repr,
)
def test_math_isclose_counts_its_defining_formula(thread_counter, arguments):
    # --- act ---------------------------------------------
    result = math.isclose(*arguments)

    # --- assert ------------------------------------------
    assert result is math.isclose(*(float(a) for a in arguments))
    # the documented formula |a-b| <= max(rel_tol * max(|a|, |b|), abs_tol), transcribed symbol
    # by symbol (max -> COMP) -- guards, short-circuit savings and the implementation's weak-test
    # respelling are the stated gap, so the charge is identical on every regime
    assert thread_counter.SUB == 1
    assert thread_counter.ABS == 3
    assert thread_counter.MUL == 1
    assert thread_counter.COMP == 3
    assert thread_counter.total_count() == 8


def test_math_isclose_without_counted_operands_counts_nothing(thread_counter):
    # --- act ---------------------------------------------
    _ = math.isclose(2.0, 2.5, rel_tol=0.5)

    # --- assert ------------------------------------------
    assert thread_counter.total_count() == 0


def test_math_isclose_negative_tolerance_counts_nothing(thread_counter):
    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="tolerances must be non-negative"):
        math.isclose(CountedFloat(2.0), 2.5, rel_tol=-1.0)
    assert thread_counter.total_count() == 0  # compute-first contract: a raised call counts nothing
