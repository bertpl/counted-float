from typing import Literal

import pytest

from counted_float._core.utils import round_number


@pytest.mark.parametrize(
    ("value", "mode", "expected_value"),
    [
        (1.123, None, 1.123),
        (0.9, "nearest_int", 1.0),
        (1.0, "nearest_int", 1.0),
        (1.7, "nearest_int", 2.0),
        (0.0, "10%", 0.0),
        (1.0, "10%", 1.0),
        (1.04, "10%", 1.0),
        (1.05, "10%", 1.1),
        (1.14, "10%", 1.1),
        (1.15, "10%", 1.2),
        (1.24, "10%", 1.2),
        (1.25, "10%", 1.3),
        (8.4, "10%", 8.0),
        (84, "10%", 80.0),
        (0.84, "10%", 0.8),
        (10.5, "10%", 11.0),  # just past the in-range upper edge: rounded via scale 10, not in-range
    ],
)
@pytest.mark.parametrize("negative", [False, True])
def test_round_number(
    value: float, mode: Literal["nearest_int", "10%"] | None, expected_value: int | float, negative: bool
):
    # --- arrange -----------------------------------------
    if negative:
        value = -value
        expected_value = -expected_value

    # --- act ---------------------------------------------
    rounded = round_number(value, mode)

    # --- assert ------------------------------------------
    assert rounded == expected_value


def test_nearest_int_mode_returns_a_float():
    # the declared return type: callers feed the result straight into float arithmetic
    # --- act ---------------------------------------------
    rounded = round_number(1.7, "nearest_int")

    # --- assert ------------------------------------------
    assert isinstance(rounded, float)
