import numpy as np

from ._geo_mean import geo_mean


def impute_missing_data(data: np.ndarray) -> np.ndarray:
    """Impute missing values in a NON-NEGATIVE matrix using a rank-1 approximation.

    This works by...
      - creating a rank-1 approximation of the matrix (ignore missing values)
      - using the approximation to fill in the missing values.

    NOTE: this will only be able to impute missing values present where both the column and row
          have at least 1 non-missing value.

    :param data:  (mxn ndarray) input data with missing values as np.nan
    :return: (mxn ndarray) data with missing values imputed, where possible
    """
    # --- rank-1 approx -----------------------------------
    # we try to approximate data = c_rows.T @ c_cols  with  c_rows > 0 and c_cols > 0
    n_rows, n_cols = data.shape[0], data.shape[1]
    c_rows, c_cols = np.ones(n_rows), np.ones(n_cols)

    e_step = 0.75  # exponent to apply to correction coefficients  (keep <1.0 for stability)
    max_iter = 100  # hard cap; the alternating correction contracts, so it converges well before this
    tol = 1e-12  # converged once the corrections stop moving the factors (see the break below)

    for _i in range(max_iter):
        # compute correction factors for c_rows
        c_row_correct = np.zeros(n_rows)
        for i_row in range(n_rows):
            # compare actual row to rank-1 approximation of row
            factors: list[float] = [
                float(data[i_row, i_col] / (c_rows[i_row] * c_cols[i_col]))
                for i_col in range(n_cols)
                if not (np.isnan(data[i_row, i_col]) or np.isnan(c_cols[i_col]) or np.isnan(c_rows[i_row]))
            ]

            # overall exact correction is geo_mean of these factors, which we'll apply with step e_step
            c_row_correct[i_row] = geo_mean(factors) ** e_step if factors else np.nan

        # compute correction factors for c_cols
        c_col_correct = np.zeros(n_cols)
        for i_col in range(n_cols):
            # compare actual col to rank-1 approximation of col
            factors = [
                float(data[i_row, i_col] / (c_rows[i_row] * c_cols[i_col]))
                for i_row in range(n_rows)
                if not (np.isnan(data[i_row, i_col]) or np.isnan(c_cols[i_col]) or np.isnan(c_rows[i_row]))
            ]

            # overall exact correction is geo_mean of these factors, which we'll apply with step e_step
            c_col_correct[i_col] = geo_mean(factors) ** e_step if factors else np.nan

        # apply corrections
        c_rows *= c_row_correct
        c_cols *= c_col_correct

        # converged once the multiplicative corrections stop moving the factors: at the rank-1
        # fixed point every correction is 1.0. Rows/cols with no data carry a NaN correction by
        # construction and are excluded from the test; an all-NaN pass (degenerate matrix) just
        # runs to max_iter.
        corrections = np.concatenate([c_row_correct, c_col_correct])
        finite = corrections[~np.isnan(corrections)]
        if finite.size and float(np.max(np.abs(finite - 1.0))) < tol:
            break

    # --- fill missing data -------------------------------
    result = data.copy()
    for i_row in range(n_rows):
        for i_col in range(n_cols):
            if np.isnan(result[i_row, i_col]) and (not np.isnan(c_rows[i_row])) and (not np.isnan(c_cols[i_col])):
                result[i_row, i_col] = c_rows[i_row] * c_cols[i_col]

    return result
