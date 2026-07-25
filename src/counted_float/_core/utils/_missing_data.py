import math

from ._geo_mean import geo_mean

# exponent applied to the correction coefficients; keep < 1.0 for stability
_E_STEP = 0.75
# hard cap; the alternating correction contracts, so it converges well before this
_MAX_ITER = 100
# converged once the corrections stop moving the factors (see the break below)
_TOL = 1e-12


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

    for _i in range(_MAX_ITER):
        # compute correction factors for c_rows
        c_row_correct = [0.0] * n_rows
        for i_row in range(n_rows):
            # compare actual row to rank-1 approximation of row
            factors: list[float] = [
                data[i_row][i_col] / (c_rows[i_row] * c_cols[i_col])
                for i_col in range(n_cols)
                if not (math.isnan(data[i_row][i_col]) or math.isnan(c_cols[i_col]) or math.isnan(c_rows[i_row]))
            ]

            # overall exact correction is geo_mean of these factors, which we'll apply with step _E_STEP
            c_row_correct[i_row] = geo_mean(factors) ** _E_STEP if factors else math.nan

        # compute correction factors for c_cols
        c_col_correct = [0.0] * n_cols
        for i_col in range(n_cols):
            # compare actual col to rank-1 approximation of col
            factors = [
                data[i_row][i_col] / (c_rows[i_row] * c_cols[i_col])
                for i_row in range(n_rows)
                if not (math.isnan(data[i_row][i_col]) or math.isnan(c_cols[i_col]) or math.isnan(c_rows[i_row]))
            ]

            # overall exact correction is geo_mean of these factors, which we'll apply with step _E_STEP
            c_col_correct[i_col] = geo_mean(factors) ** _E_STEP if factors else math.nan

        # apply corrections
        c_rows = [c * correction for c, correction in zip(c_rows, c_row_correct, strict=True)]
        c_cols = [c * correction for c, correction in zip(c_cols, c_col_correct, strict=True)]

        # converged once the multiplicative corrections stop moving the factors: at the rank-1
        # fixed point every correction is 1.0. Rows/cols with no data carry a NaN correction by
        # construction and are excluded from the test; an all-NaN pass (degenerate matrix) just
        # runs to _MAX_ITER.
        finite = [c for c in (c_row_correct + c_col_correct) if not math.isnan(c)]
        if finite and max(abs(c - 1.0) for c in finite) < _TOL:
            break

    # --- fill missing data -------------------------------
    result = [row[:] for row in data]
    for i_row in range(n_rows):
        for i_col in range(n_cols):
            if math.isnan(result[i_row][i_col]) and not (math.isnan(c_rows[i_row]) or math.isnan(c_cols[i_col])):
                result[i_row][i_col] = c_rows[i_row] * c_cols[i_col]

    return result
