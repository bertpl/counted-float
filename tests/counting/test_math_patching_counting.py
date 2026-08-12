import math

import pytest

from counted_float._core.counting import math_patching
from counted_float._core.counting.counted_float import CountedFloat

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
        # plain-float delegation paths for the special functions; their CountedFloat counting
        # paths are exercised by the golden corpus.
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


# =================================================================================================
#  Patched math functions - delegation the corpus cannot observe
# =================================================================================================
def test_prod_without_counted_values_forwards_a_non_default_start(thread_counter):
    # the all-plain path delegates to the original; it must forward `start`, not drop it
    # --- act / assert ------------------------------------
    result = math.prod([2, 3, 4], start=10)
    assert result == 240  # 10 * 2 * 3 * 4, not the start-dropped 24
    assert thread_counter.total_count() == 0


def test_math_isclose_negative_tolerance_counts_nothing(thread_counter):
    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="tolerances must be non-negative"):
        math.isclose(CountedFloat(2.0), 2.5, rel_tol=-1.0)
    assert thread_counter.total_count() == 0  # compute-first contract: a raised call counts nothing


# =================================================================================================
#  Patched math functions - version-gated registration
# =================================================================================================
def test_math_fma_registered_only_where_available():
    """math.fma is patched exactly on the interpreters that have it, and never elsewhere."""
    # --- act & assert ------------------------------------
    assert ("fma" in math_patching._PATCHES) == hasattr(math, "fma")


_PY315_NAMES = ["fmax", "fmin", "isnormal", "issubnormal", "signbit"]


@pytest.mark.parametrize("fname", _PY315_NAMES)
def test_py315_math_functions_registered_only_where_available(fname):
    """Each 3.15 callable is patched exactly on the interpreters that have it, and never elsewhere."""
    # --- act & assert ------------------------------------
    assert (fname in math_patching._PATCHES) == hasattr(math, fname)
