import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from counted_float._core.utils import geo_mean


@pytest.mark.parametrize(
    ("values", "expected_result"),
    [
        ([0, 1, 1], 0.0),
        ([1, 1, 1], 1.0),
        ([1, 10, 100], 10.0),
        ([2, 8], 4.0),
        ([5], 5.0),  # edge case: single value
        ([1e200, 1e200, 1e200], 1e200),  # would overflow the naive product-then-root form
    ],
)
def test_geo_mean(values: list, expected_result: float):
    # --- act ---------------------------------------------
    result = geo_mean(values)

    # --- assert ------------------------------------------
    assert result == pytest.approx(expected_result, rel=1e-12, abs=1e-12)


def test_geo_mean_nan_propagates():
    # --- act & assert ------------------------------------
    assert math.isnan(geo_mean([1.0, math.nan, 4.0]))


@pytest.mark.parametrize("values", [[], [1.0, -2.0]])
def test_geo_mean_rejects_degenerate_input(values: list):
    # empty input and negative values would silently poison downstream aggregates
    # --- act & assert ------------------------------------
    with pytest.raises(ValueError, match="geo_mean"):
        geo_mean(values)


# =================================================================================================
#  Property-based coverage
# =================================================================================================
_positive = st.floats(min_value=1e-6, max_value=1e12, allow_nan=False, allow_infinity=False)


@given(values=st.lists(_positive, min_size=1, max_size=20))
def test_geo_mean_lies_between_the_min_and_max(values: list[float]):
    # --- act ---------------------------------------------
    result = geo_mean(values)

    # --- assert ------------------------------------------
    assert min(values) <= result <= max(values) or math.isclose(result, min(values), rel_tol=1e-9)


@given(value=_positive, n=st.integers(min_value=1, max_value=20))
def test_geo_mean_of_a_constant_list_is_that_constant(value: float, n: int):
    # --- act / assert ------------------------------------
    assert math.isclose(geo_mean([value] * n), value, rel_tol=1e-9)


@given(values=st.lists(_positive, min_size=1, max_size=15), factor=_positive)
def test_geo_mean_scales_with_its_inputs(values: list[float], factor: float):
    """geo_mean(k*x) == k*geo_mean(x): a homogeneity the weighting relies on."""
    # --- act ---------------------------------------------
    scaled = geo_mean([factor * v for v in values])

    # --- assert ------------------------------------------
    assert math.isclose(scaled, factor * geo_mean(values), rel_tol=1e-9)


@given(values=st.lists(_positive, min_size=1, max_size=20))
def test_geo_mean_does_not_exceed_the_arithmetic_mean(values: list[float]):
    """The AM-GM inequality: a basic sanity bound the log-space form must still respect."""
    # --- act ---------------------------------------------
    arithmetic_mean = sum(values) / len(values)

    # --- assert ------------------------------------------
    # relative slack: at large magnitudes the two means differ only in float-noise digits
    assert geo_mean(values) <= arithmetic_mean * (1 + 1e-9)


@given(values=st.lists(_positive, min_size=1, max_size=10))
def test_a_single_zero_makes_the_geo_mean_zero(values: list[float]):
    # --- act / assert ------------------------------------
    assert geo_mean([*values, 0.0]) == 0.0
