import math

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

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


# =================================================================================================
#  Property-based coverage
# =================================================================================================
# a filled cell has no ground truth to check against, so these pin structural invariants rather than
# values: what the imputation must never do, and the one case where it must reproduce the input.
_finite = st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False)


@st.composite
def _rank1_matrices(draw):
    """A strictly-positive rank-1 matrix (outer product of two positive vectors)."""
    n_rows = draw(st.integers(min_value=1, max_value=6))
    n_cols = draw(st.integers(min_value=1, max_value=6))
    rows = np.array(draw(st.lists(_finite, min_size=n_rows, max_size=n_rows)))
    cols = np.array(draw(st.lists(_finite, min_size=n_cols, max_size=n_cols)))
    return np.outer(rows, cols)


@given(matrix=_rank1_matrices(), mask=st.data())
def test_an_exactly_rank1_matrix_is_recovered(matrix: np.ndarray, mask):
    """The model is rank-1, so a rank-1 input must be reproduced at its missing cells."""
    # --- arrange -----------------------------------------
    holed = matrix.copy()
    n_rows, n_cols = matrix.shape
    # knock out one interior cell, leaving its row and col with evidence so it is fillable
    if n_rows >= 2 and n_cols >= 2:
        i = mask.draw(st.integers(min_value=0, max_value=n_rows - 1))
        j = mask.draw(st.integers(min_value=0, max_value=n_cols - 1))
        holed[i, j] = np.nan

        # --- act -----------------------------------------
        filled = impute_missing_data(holed)

        # --- assert --------------------------------------
        assert math.isclose(filled[i, j], matrix[i, j], rel_tol=1e-6)


@given(matrix=_rank1_matrices())
def test_present_values_are_left_untouched(matrix: np.ndarray):
    # --- arrange -----------------------------------------
    holed = matrix.copy()
    if matrix.size >= 2:
        holed.flat[0] = np.nan

    # --- act ---------------------------------------------
    filled = impute_missing_data(holed)

    # --- assert ------------------------------------------
    present = ~np.isnan(holed)
    assert np.allclose(filled[present], matrix[present])


@given(matrix=_rank1_matrices())
def test_fills_are_never_negative(matrix: np.ndarray):
    # --- arrange -----------------------------------------
    holed = matrix.copy()
    if matrix.size >= 2:
        holed.flat[0] = np.nan

    # --- act ---------------------------------------------
    filled = impute_missing_data(holed)

    # --- assert ------------------------------------------
    filled_cells = filled[~np.isnan(filled)]
    assert np.all(filled_cells >= 0)


def test_a_cell_with_no_row_or_column_evidence_stays_missing():
    # --- arrange -----------------------------------------
    # the whole first row is missing, so its cells have no row evidence to lean on
    data = np.array([[np.nan, np.nan], [3.0, 6.0]])

    # --- act ---------------------------------------------
    filled = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert np.all(np.isnan(filled[0, :]))  # unfillable cells are left as-is, not invented
