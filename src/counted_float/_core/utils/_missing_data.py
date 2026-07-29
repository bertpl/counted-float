import math
import sys
import warnings

from ._geo_mean import geo_mean

# hard cap on fitting sweeps; each sweep below is an exact alternating fit, so this is only ever
# reached for pathologically weakly-connected observation patterns -- in which case a
# RuntimeWarning is raised rather than truncating silently
_MAX_ITER = 250


def _reachable_tolerance(n_rows: int, n_cols: int) -> float:
    """Convergence floor for a matrix of this size: one ulp per averaged term, near enough.

    Every correction is a geometric mean over at most one full row or column, so rounding can
    accumulate on the order of one ulp per term averaged -- bounded by the larger dimension, since
    a row correction averages across columns and a column correction across rows. Below that the
    corrections are floating-point noise rather than signal, and no number of further sweeps
    reduces them.

    Derived rather than fixed because a constant cannot be right for every size: too loose and a
    small matrix stops early, too tight and a large one can never satisfy it and would spin to the
    sweep cap on every call.
    """
    return max(n_rows, n_cols) * sys.float_info.epsilon


def _axis_corrections(matrix: list[list[float]], own: list[float], other: list[float]) -> list[float]:
    """Geometric-mean correction factor per row of `matrix`, against the current rank-1 estimate.

    Rows of `matrix` are scaled by `own` and its columns by `other`, so passing the transpose with
    the two factor lists swapped performs the column-wise pass: it is the same computation with the
    axes exchanged, which is why it is written once. Rows whose own factor is unknown, and entries
    whose value or opposing factor is unknown, carry no information and are skipped; a row left with
    nothing to compare against gets a NaN correction.

    The geometric mean is the *exact* correction in log space: applied in full, it minimizes the
    sum of squared log-residuals over this axis' factors, holding the other axis' factors fixed.
    """
    corrections: list[float] = []
    for i, row in enumerate(matrix):
        own_is_missing = math.isnan(own[i])
        factors = [
            value / (own[i] * other[j])
            for j, value in enumerate(row)
            if not (own_is_missing or math.isnan(value) or math.isnan(other[j]))
        ]
        corrections.append(geo_mean(factors) if factors else math.nan)
    return corrections


def impute_missing_data(data: list[list[float]]) -> list[list[float]]:
    """Impute missing values in a STRICTLY-POSITIVE matrix using a rank-1 approximation.

    This works by...
      - creating a rank-1 approximation of the matrix (ignore missing values)
      - using the approximation to fill in the missing values.

    The work is per-element by nature — a geometric mean of ratios taken row-wise then column-wise —
    so it is expressed over plain lists. An array library buys nothing here and costs the boxing of
    every scalar read.

    NOTE: this will only be able to impute missing values present where both the column and row
          have at least 1 non-missing value.
    NOTE: present values must be strictly positive: the model is multiplicative, so a 0 collapses
          the factors of its row and column and poisons every cell they touch.
    NOTE: if the observed cells fall apart into groups of rows/columns with no observed cell
          linking them, a fill bridging two groups is only determined up to an arbitrary scale
          between those groups and is therefore not meaningful.

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
    tolerance = _reachable_tolerance(n_rows, n_cols)

    for _i in range(_MAX_ITER):
        # alternating exact fits (coordinate descent in log space): fit the row factors against the
        # current column factors, then fit the column factors against the *updated* row factors.
        # Each half-sweep exactly minimizes the squared log-residuals over its own factors, so the
        # fit improves monotonically and needs no damping. (Computing both halves from the same
        # stale factors would absorb the shared scale twice per sweep -- an overshoot that must be
        # damped for stability and then converges far more slowly.)
        c_row_correct = _axis_corrections(data, c_rows, c_cols)
        c_rows = [c * correction for c, correction in zip(c_rows, c_row_correct, strict=True)]
        c_col_correct = _axis_corrections(transposed, c_cols, c_rows)
        c_cols = [c * correction for c, correction in zip(c_cols, c_col_correct, strict=True)]

        # converged once the corrections stop moving the factors: at the rank-1 fixed point every
        # correction is 1.0. Rows/cols with no data carry a NaN correction by construction and are
        # excluded from the test.
        finite = [c for c in (c_row_correct + c_col_correct) if not math.isnan(c)]
        if not finite:
            # nothing anywhere to fit against: every factor is now NaN and no later pass can undo
            # that, so the remaining iterations would recompute the same nothing
            break
        if max(abs(c - 1.0) for c in finite) < tolerance:
            break
    else:
        warnings.warn(
            f"rank-1 imputation did not reach tolerance {tolerance:g} within {_MAX_ITER} sweeps; "
            f"imputed values may be inaccurate. This indicates an extremely weakly-connected "
            f"pattern of observed cells.",
            RuntimeWarning,
            stacklevel=2,
        )

    # --- fill missing data -------------------------------
    result = [row[:] for row in data]
    for i_row in range(n_rows):
        for i_col in range(n_cols):
            if math.isnan(result[i_row][i_col]) and not (math.isnan(c_rows[i_row]) or math.isnan(c_cols[i_col])):
                result[i_row][i_col] = c_rows[i_row] * c_cols[i_col]

    return result
