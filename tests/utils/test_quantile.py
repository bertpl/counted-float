"""The internal quantile must agree with numpy's default method, exactly.

The benchmark results' summary statistics were taken with `np.quantile` before numpy was removed
from everything the counting path can reach. Keeping the two bit-identical is what makes that a
substitution rather than a change: previously collected results summarize to the same numbers, and
the shipped weights derived from them stay reproducible.

Wherever numpy is available the equivalence is pinned against the real thing rather than against a
table of expected values; where it is not, there is nothing left to compare against and the module
skips.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from counted_float._core.utils import quantile

np = pytest.importorskip("numpy", reason="the equivalence is pinned against the real numpy")

_QUANTILES_USED = [0.10, 0.25, 0.50, 0.75]

_FINITE_SAMPLES = st.lists(
    st.floats(min_value=-1e12, max_value=1e12, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=40,
)


# =================================================================================================
#  Equivalence with numpy
# =================================================================================================
@given(values=_FINITE_SAMPLES, q=st.sampled_from(_QUANTILES_USED))
def test_matches_numpy_on_the_quantiles_the_library_takes(values: list[float], q: float):
    # --- act ---------------------------------------------
    ours, theirs = quantile(values, q), float(np.quantile(values, q))

    # --- assert ------------------------------------------
    assert ours == theirs, f"q={q} over {values}: {ours!r} != {theirs!r}"


@given(values=_FINITE_SAMPLES, q=st.floats(min_value=0.0, max_value=1.0))
def test_matches_numpy_on_any_quantile(values: list[float], q: float):
    # --- act ---------------------------------------------
    ours, theirs = quantile(values, q), float(np.quantile(values, q))

    # --- assert ------------------------------------------
    assert ours == theirs, f"q={q} over {values}: {ours!r} != {theirs!r}"


# =================================================================================================
#  Edge cases and rejections
# =================================================================================================
@pytest.mark.parametrize("q", _QUANTILES_USED)
def test_a_single_value_is_its_own_quantile(q: float):
    # --- act / assert ------------------------------------
    assert quantile([42.0], q) == 42.0


def test_the_extremes_are_the_order_statistics():
    # --- arrange -----------------------------------------
    values = [3.0, 1.0, 2.0]

    # --- act / assert ------------------------------------
    assert quantile(values, 0.0) == 1.0
    assert quantile(values, 1.0) == 3.0


def test_an_empty_sample_is_rejected():
    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match=r"^quantile of an empty sample is undefined$"):
        quantile([], 0.5)


@pytest.mark.parametrize("q", [-0.01, 1.01, math.inf, -math.inf])
def test_a_quantile_outside_the_unit_interval_is_rejected(q: float):
    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match=r"must lie in \[0, 1\]"):
        quantile([1.0, 2.0], q)
