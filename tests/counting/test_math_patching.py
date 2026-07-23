import math
import subprocess
import sys

import pytest

from counted_float import FlopCountingContext
from counted_float._core.counting import _math_patching
from counted_float._core.counting._counted_float import CountedFloat

from .conftest import PATCHED_FUNCTION_NAMES, STDLIB_MATH_FUNCTIONS


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


# =================================================================================================
#  Patch snapshot capture and restore
# =================================================================================================


def test_unbalanced_remove_math_patches_does_not_clobber_a_later_patch():
    """An unbalanced removal must not re-apply the snapshot over a third-party patch."""
    # --- arrange -----------------------------------------
    with FlopCountingContext():
        pass  # patches applied and restored; the snapshot has served its purpose

    def third_party_sqrt(x: float) -> float:
        return x

    original_sqrt = math.sqrt
    math.sqrt = third_party_sqrt  # ty: ignore[invalid-assignment]

    # --- act ---------------------------------------------
    try:
        _math_patching.remove_math_patches()  # unbalanced: no context is open
        survived = math.sqrt is third_party_sqrt
    finally:
        math.sqrt = original_sqrt  # ty: ignore[invalid-assignment]

    # --- assert ------------------------------------------
    assert survived


def test_capture_originals_keeps_both_original_tables_in_sync():
    """Every patched function's delegation global must match its restoration entry.

    The originals are captured twice over: a module global per function, which the counting
    replacements delegate to, and a dict used to restore the module afterwards. Adding a patch
    while forgetting its global leaves restoration working while delegation silently calls a
    stale import-time reference, so nothing downstream would notice.
    """
    # --- act ---------------------------------------------
    _math_patching._capture_originals()

    # --- assert ------------------------------------------
    for name in _math_patching._PATCHES:
        delegation_target = getattr(_math_patching, f"original_math_{name}", None)
        assert delegation_target is not None, f"no original_math_{name} global for patched '{name}'"
        assert delegation_target is _math_patching._saved_originals[name], (
            f"original_math_{name} does not match the restoration snapshot for '{name}'"
        )


# =================================================================================================
#  Version-gated stand-ins and teardown guard
# =================================================================================================
def test_fma_unavailable_stand_in_raises() -> None:
    # the stand-in exists so original_math_fma is callable pre-3.13; calling it must raise
    # --- act / assert ------------------------------------
    with pytest.raises(NotImplementedError, match=r"math\.fma"):
        _math_patching._math_fma_unavailable(1.0, 2.0, 3.0)


def test_sumprod_unavailable_stand_in_raises() -> None:
    # --- act / assert ------------------------------------
    with pytest.raises(NotImplementedError, match=r"math\.sumprod"):
        _math_patching._math_sumprod_unavailable([1.0], [2.0])


def test_remove_uncounted_math_patches_is_a_noop_when_none_installed() -> None:
    # the guard returns early when no thread is reporting, so there is nothing to undo
    # --- arrange -----------------------------------------
    assert _math_patching._reporting_thread_count == 0

    # --- act / assert (must not raise or touch the math module) ---
    _math_patching.remove_uncounted_math_patches()
    assert _math_patching._reporting_thread_count == 0
