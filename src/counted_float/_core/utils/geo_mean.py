import math


def geo_mean(values: list[float | int]) -> float:
    """Take the geometric mean of a list of values, computed in log-space.

    Log-space summation avoids the overflow the naive product-then-root form hits for
    large corpora or large raw costs.  nan values propagate (nan in -> nan out), a zero
    yields 0.0, negative values and an empty list are rejected: both would silently
    poison downstream aggregates (a negative product can turn a fractional root complex).
    """
    if len(values) == 0:
        raise ValueError("geo_mean of an empty list is undefined")
    if any(v < 0 for v in values):
        raise ValueError("geo_mean requires non-negative values")
    if any(v == 0 for v in values):
        return 0.0
    return math.exp(math.fsum(math.log(v) for v in values) / len(values))
