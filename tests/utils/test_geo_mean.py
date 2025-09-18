import pytest

from counted_float._core.utils import geo_mean


@pytest.mark.parametrize(
    "values, expected_result",
    [
        ([0, 1, 1], 0.0),
        ([1, 1, 1], 1.0),
        ([1, 10, 100], 10.0),
        ([2, 8], 4.0),
        ([], 0.0),  # edge case: empty list
        ([5], 5.0),  # edge case: single value
    ],
)
def test_geo_mean(values: list, expected_result: float):
    # --- act ---------------------------------------------
    result = geo_mean(values)

    # --- assert ------------------------------------------
    assert result == pytest.approx(expected_result, rel=1e-14, abs=1e-14)
