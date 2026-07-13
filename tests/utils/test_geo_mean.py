import math

import pytest

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
