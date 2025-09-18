import math

import numpy as np

from counted_float._core.utils import impute_missing_data


def test_impute_missing_data_full_matrix():
    # --- arrange -----------------------------------------
    data = np.array(
        [
            [1, 2, 3],
            [2, 4, 6],
            [3, 6, 10],
        ]
    )

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert np.array_equal(data, filled_data)


def test_impute_missing_data_missing_row():
    # --- arrange -----------------------------------------
    data = np.array(
        [
            [1, 2, 3],
            [2, 4, 6],
            [math.nan, math.nan, math.nan],
        ]
    )

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert np.array_equal(data, filled_data, equal_nan=True)


def test_impute_missing_data_missing_col():
    # --- arrange -----------------------------------------
    data = np.array(
        [
            [1, 2, math.nan],
            [2, 4, math.nan],
            [3, 6, math.nan],
        ]
    )

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert np.array_equal(data, filled_data, equal_nan=True)


def test_impute_missing_data_partial_matrix():
    # --- arrange -----------------------------------------
    data = np.array(
        [
            [math.nan, 2, 3],
            [2, 4, math.nan],
            [math.nan, 6, math.nan],
        ],
        dtype=float,
    )

    expected = np.array(
        [
            [1, 2, 3],
            [2, 4, 6],
            [3, 6, 9],
        ],
        dtype=float,
    )

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    print(filled_data)

    # --- assert ------------------------------------------
    assert np.allclose(filled_data, expected, rtol=1e-10, atol=1e-10)


def test_impute_missing_data_mixed_case():
    # --- arrange -----------------------------------------
    data = np.array(
        [
            [1, 2, math.nan],
            [2, math.nan, math.nan],
            [math.nan, math.nan, math.nan],
        ],
        dtype=float,
    )

    expected = np.array(
        [
            [1, 2, math.nan],
            [2, 4, math.nan],
            [math.nan, math.nan, math.nan],
        ],
        dtype=float,
    )

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    print(filled_data)

    # --- assert ------------------------------------------
    assert np.allclose(filled_data, expected, rtol=1e-10, atol=1e-10, equal_nan=True)
