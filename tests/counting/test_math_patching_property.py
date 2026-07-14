"""Property-based test: a raised ``math.*`` call never leaves a phantom flop count.

Every patched math function counts on the *success* path only — if the underlying call raises
(domain error, overflow, ...), the active counting context must be left unchanged. Six
single-argument functions (``sqrt``, ``log``, ``log2``, ``log10``, ``exp``, ``exp2``) once
counted *before* the underlying call and leaked a count on the exception path; this property
blankets the whole patched set so that class of bug can't recur silently. The success-path,
per-op counting is covered point-by-point in ``test_math_patching.py``.
"""

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from counted_float import CountedFloat
from counted_float._core.counting import _math_patching

_PATCHED_NAMES = sorted(_math_patching._PATCHES.keys())
_BINARY = {"atan2", "hypot", "fmod", "pow"}  # invoked with two operands; the rest take one


@pytest.mark.parametrize("fname", _PATCHED_NAMES)
@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(x=st.floats(allow_nan=True, allow_infinity=True, width=64))
def test_raising_math_call_leaves_count_unchanged(global_counter, fname: str, x: float) -> None:
    # --- arrange -----------------------------------------
    func = getattr(math, fname)  # the fixture keeps a context active, so this is the patched version
    args = (CountedFloat(x), CountedFloat(x)) if fname in _BINARY else (CountedFloat(x),)
    global_counter.reset()

    # --- act / assert ------------------------------------
    try:
        func(*args)
    except (ValueError, OverflowError):
        # compute-first contract: a raised call counts nothing
        assert global_counter.total_count() == 0
