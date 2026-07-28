import math

from ._geo_mean import geo_mean

# exponent applied to the correction coefficients; keep < 1.0 for stability
_E_STEP = 0.75
# hard cap; the alternating correction contracts, so it converges well before this
_MAX_ITER = 100
# converged once the corrections stop moving the factors (see the break below)
_TOL = 1e-12


def _axis_corrections(matrix: list[list[float]], own: list[float], other: list[float]) -> list[float]:
    """Geometric-mean correction factor per row of `matrix`, against the current rank-1 estimate.

    Rows of `matrix` are scaled by `own` and its columns by `other`, so passing the transpose with
    the two factor lists swapped performs the column-wise pass: it is the same computation with the
    axes exchanged, which is why it is written once. Rows whose own factor is unknown, and entries
    whose value or opposing factor is unknown, carry no information and are skipped; a row left with
    nothing to compare against gets a NaN correction.
    """
    corrections: list[float] = []
    for i, row in enumerate(matrix):
        own_is_missing = math.isnan(own[i])
        factors = [
            value / (own[i] * other[j])
            for j, value in enumerate(row)
            if not (own_is_missing or math.isnan(value) or math.isnan(other[j]))
        ]
        # the exact correction is the geometric mean of those factors, applied at step _E_STEP
        corrections.append(geo_mean(factors) ** _E_STEP if factors else math.nan)
    return corrections


def impute_missing_data(data: list[list[float]]) -> list[list[float]]:
    """Impute missing values in a NON-NEGATIVE matrix using a rank-1 approximation.

    This works by...
      - creating a rank-1 approximation of the matrix (ignore missing values)
      - using the approximation to fill in the missing values.

    The work is per-element by nature — a geometric mean of ratios taken row-wise then column-wise —
    so it is expressed over plain lists. An array library buys nothing here and costs the boxing of
    every scalar read.

    NOTE: this will only be able to impute missing values present where both the column and row
          have at least 1 non-missing value.

    Args:
        data: Row-major matrix with missing values marked as `math.nan`. Left unmodified.

    Returns:
        A new matrix with missing values imputed where possible, the rest still `math.nan`.
    """
    # --- rank-1 approx -----------------------------------
    # we try to approximate data = c_rows.T @ c_cols  with  c_rows > 0 and c_cols > 0
    n_rows, n_cols = len(data), len(data[0])
    c_rows, c_cols = [1.0] * n_rows, [1.0] * n_cols

    # loop-invariant: `data` is documented as unmodified, so transposing once outside the loop
    # rather than per iteration costs one copy instead of _MAX_ITER of them
    transposed = [list(column) for column in zip(*data, strict=True)]

    for _i in range(_MAX_ITER):
        # the two passes are one computation with the axes exchanged: rows scaled by c_rows against
        # c_cols, then the transpose scaled by c_cols against c_rows. Both read the factors as they
        # were at the top of the iteration -- a symmetric update -- so neither pass may apply its
        # corrections before the other has been computed.
        c_row_correct = _axis_corrections(data, c_rows, c_cols)
        c_col_correct = _axis_corrections(transposed, c_cols, c_rows)

        # apply corrections
        c_rows = [c * correction for c, correction in zip(c_rows, c_row_correct, strict=True)]
        c_cols = [c * correction for c, correction in zip(c_cols, c_col_correct, strict=True)]

        # converged once the multiplicative corrections stop moving the factors: at the rank-1
        # fixed point every correction is 1.0. Rows/cols with no data carry a NaN correction by
        # construction and are excluded from the test.
        finite = [c for c in (c_row_correct + c_col_correct) if not math.isnan(c)]
        if not finite:
            # nothing anywhere to fit against: every factor is now NaN and no later pass can undo
            # that, so the remaining iterations would recompute the same nothing
            break
        if max(abs(c - 1.0) for c in finite) < _TOL:
            break

    # --- fill missing data -------------------------------
    result = [row[:] for row in data]
    for i_row in range(n_rows):
        for i_col in range(n_cols):
            if math.isnan(result[i_row][i_col]) and not (math.isnan(c_rows[i_row]) or math.isnan(c_cols[i_col])):
                result[i_row][i_col] = c_rows[i_row] * c_cols[i_col]

    return result
