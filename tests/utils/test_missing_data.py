import math
import warnings

import pytest
from hypothesis import given
from hypothesis import strategies as st

from counted_float._core.utils import _missing_data, impute_missing_data

Matrix = list[list[float]]


# =================================================================================================
#  Helpers
# =================================================================================================
def _same(actual: Matrix, expected: Matrix, *, rel_tol: float = 1e-10) -> bool:
    """Whether two matrices agree cell by cell, counting two missing markers as agreeing."""
    if [len(row) for row in actual] != [len(row) for row in expected]:
        return False
    return all(
        (math.isnan(a) and math.isnan(e)) or math.isclose(a, e, rel_tol=rel_tol, abs_tol=1e-10)
        for row_a, row_e in zip(actual, expected, strict=True)
        for a, e in zip(row_a, row_e, strict=True)
    )


def _outer(rows: list[float], cols: list[float]) -> Matrix:
    """The rank-1 matrix formed by two positive vectors."""
    return [[r * c for c in cols] for r in rows]


# =================================================================================================
#  Worked cases
# =================================================================================================
def test_impute_missing_data_full_matrix():
    # --- arrange -----------------------------------------
    data = [
        [1, 2, 3],
        [2, 4, 6],
        [3, 6, 10],
    ]

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert _same(filled_data, data)


def test_impute_missing_data_missing_row():
    # --- arrange -----------------------------------------
    data = [
        [1, 2, 3],
        [2, 4, 6],
        [math.nan, math.nan, math.nan],
    ]

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert _same(filled_data, data)


def test_impute_missing_data_missing_col():
    # --- arrange -----------------------------------------
    data = [
        [1, 2, math.nan],
        [2, 4, math.nan],
        [3, 6, math.nan],
    ]

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert _same(filled_data, data)


def test_impute_missing_data_partial_matrix():
    # --- arrange -----------------------------------------
    data = [
        [math.nan, 2, 3],
        [2, 4, math.nan],
        [math.nan, 6, math.nan],
    ]
    expected = [
        [1, 2, 3],
        [2, 4, 6],
        [3, 6, 9],
    ]

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert _same(filled_data, expected)


def test_impute_missing_data_mixed_case():
    # --- arrange -----------------------------------------
    data = [
        [1, 2, math.nan],
        [2, math.nan, math.nan],
        [math.nan, math.nan, math.nan],
    ]
    expected = [
        [1, 2, math.nan],
        [2, 4, math.nan],
        [math.nan, math.nan, math.nan],
    ]

    # --- act ---------------------------------------------
    filled_data = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert _same(filled_data, expected)


def test_the_input_is_not_modified():
    # --- arrange -----------------------------------------
    data = [
        [1.0, 2.0],
        [math.nan, 4.0],
    ]

    # --- act ---------------------------------------------
    impute_missing_data(data)

    # --- assert ------------------------------------------
    assert math.isnan(data[1][0])  # the hole is still a hole in the caller's own matrix


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
    rows = draw(st.lists(_finite, min_size=n_rows, max_size=n_rows))
    cols = draw(st.lists(_finite, min_size=n_cols, max_size=n_cols))
    return _outer(rows, cols)


@given(matrix=_rank1_matrices(), mask=st.data())
def test_an_exactly_rank1_matrix_is_recovered(matrix: Matrix, mask):
    """The model is rank-1, so a rank-1 input must be reproduced at its missing cells."""
    # --- arrange -----------------------------------------
    n_rows, n_cols = len(matrix), len(matrix[0])
    # knock out one interior cell, leaving its row and col with evidence so it is fillable
    if n_rows >= 2 and n_cols >= 2:
        i = mask.draw(st.integers(min_value=0, max_value=n_rows - 1))
        j = mask.draw(st.integers(min_value=0, max_value=n_cols - 1))
        holed = [row[:] for row in matrix]
        holed[i][j] = math.nan

        # --- act -----------------------------------------
        filled = impute_missing_data(holed)

        # --- assert --------------------------------------
        assert math.isclose(filled[i][j], matrix[i][j], rel_tol=1e-6)


@given(matrix=_rank1_matrices())
def test_present_values_are_left_untouched(matrix: Matrix):
    # --- arrange -----------------------------------------
    holed = [row[:] for row in matrix]
    if len(matrix) * len(matrix[0]) >= 2:
        holed[0][0] = math.nan

    # --- act ---------------------------------------------
    filled = impute_missing_data(holed)

    # --- assert ------------------------------------------
    assert all(
        filled[i][j] == matrix[i][j]
        for i in range(len(matrix))
        for j in range(len(matrix[0]))
        if not math.isnan(holed[i][j])
    )


@given(matrix=_rank1_matrices())
def test_fills_are_never_negative(matrix: Matrix):
    # --- arrange -----------------------------------------
    holed = [row[:] for row in matrix]
    if len(matrix) * len(matrix[0]) >= 2:
        holed[0][0] = math.nan

    # --- act ---------------------------------------------
    filled = impute_missing_data(holed)

    # --- assert ------------------------------------------
    assert all(value >= 0 for row in filled for value in row if not math.isnan(value))


def test_a_cell_with_no_row_or_column_evidence_stays_missing():
    # --- arrange -----------------------------------------
    # the whole first row is missing, so its cells have no row evidence to lean on
    data = [[math.nan, math.nan], [3.0, 6.0]]

    # --- act ---------------------------------------------
    filled = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert all(math.isnan(value) for value in filled[0])  # unfillable cells are left as-is, not invented


def test_a_fully_missing_matrix_is_returned_unchanged():
    """With nothing anywhere to fit against, every cell stays missing.

    This is the degenerate input the fitting loop exits early on: no row and no column carries a
    usable value, so every correction factor is unknown from the first pass onward and no later
    pass can change that.
    """
    # --- arrange -----------------------------------------
    data = [[math.nan] * 3 for _ in range(2)]

    # --- act ---------------------------------------------
    result = impute_missing_data(data)

    # --- assert ------------------------------------------
    assert all(math.isnan(value) for row in result for value in row)
    assert len(result) == 2
    assert all(len(row) == 3 for row in result)


# =================================================================================================
#  Convergence
# =================================================================================================
# each sweep is an exact alternating fit, so even weakly-connected observation patterns must be
# recovered well inside the sweep budget; these pin that against regressions to damped or
# stale-update schemes, which crawl on exactly such patterns.


def _two_blocks_with_thin_coupling(n: int = 10) -> tuple[Matrix, Matrix]:
    """An exact rank-1 matrix observed as two blocks that share only two columns.

    The top rows are observed on the left columns, the bottom rows on the right columns, with an
    overlap of two shared columns: all information linking the two blocks flows through that
    overlap. This mirrors the structure of the built-in weights matrix (spec-only vs
    benchmark-only sources), the pattern on which a damped simultaneous-update scheme previously
    exhausted its sweep budget.
    """
    rows = [1.5**i for i in range(n)]
    cols = [0.5 * 1.8**j for j in range(n)]
    full = _outer(rows, cols)
    half = n // 2
    holed = [
        [
            value if ((i < half and j <= half) or (i >= half and j >= half - 1)) else math.nan
            for j, value in enumerate(row)
        ]
        for i, row in enumerate(full)
    ]
    return holed, full


def test_a_thinly_coupled_block_pattern_is_recovered_within_120_sweeps(monkeypatch):
    # A budget that separates the two schemes on this pattern: alternating exact fits reach the
    # tolerance in 84 sweeps, while computing both halves from stale factors needs 208. Raising the
    # warning to an error is what makes the name true -- without it the case would still pass on a
    # truncated fit that happened to land close enough.
    # --- arrange -----------------------------------------
    holed, full = _two_blocks_with_thin_coupling()
    monkeypatch.setattr(_missing_data, "_MAX_ITER", 120)

    # --- act ---------------------------------------------
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        filled = impute_missing_data(holed)

    # --- assert ------------------------------------------
    assert _same(filled, full, rel_tol=1e-8)


def test_exceeding_the_sweep_budget_warns_instead_of_truncating_silently(monkeypatch):
    # --- arrange -----------------------------------------
    # a single sweep can never satisfy the convergence test: its corrections *are* the initial fit
    holed, _ = _two_blocks_with_thin_coupling()
    monkeypatch.setattr(_missing_data, "_MAX_ITER", 1)

    # --- act / assert ------------------------------------
    with pytest.warns(RuntimeWarning, match="did not reach tolerance"):
        impute_missing_data(holed)


@given(matrix=_rank1_matrices(), mask=st.data())
def test_any_pattern_anchored_by_a_full_row_and_column_is_recovered(matrix: Matrix, mask):
    """With row 0 and column 0 fully observed, every cell stays linked to one evidence group, so
    arbitrary further missingness must still be recovered exactly for rank-1 input."""
    # --- arrange -----------------------------------------
    n_rows, n_cols = len(matrix), len(matrix[0])
    holed = [row[:] for row in matrix]
    for i in range(1, n_rows):
        for j in range(1, n_cols):
            if mask.draw(st.booleans()):
                holed[i][j] = math.nan

    # --- act ---------------------------------------------
    filled = impute_missing_data(holed)

    # --- assert ------------------------------------------
    assert _same(filled, matrix, rel_tol=1e-6)
