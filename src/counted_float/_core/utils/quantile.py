import math


def quantile(values: list[float], q: float) -> float:
    """Linear-interpolated quantile of a sample, matching numpy's default method exactly.

    The sample is ordered and `q` addressed as a virtual index into it, blending the two
    neighbouring order statistics when that index falls between them.

    Args:
        values: The sample; left unmodified. A single value is enough — it is its own quantile.
        q: Quantile to take, in [0, 1].

    Returns:
        The interpolated value at `q`.

    Raises:
        ValueError: If `values` is empty, or `q` lies outside [0, 1].
    """
    if not values:
        raise ValueError("quantile of an empty sample is undefined")
    if not 0.0 <= q <= 1.0:
        raise ValueError(f"quantile q must lie in [0, 1], got {q}")

    ordered = sorted(values)
    virtual_index = (len(ordered) - 1) * q
    below, above = math.floor(virtual_index), math.ceil(virtual_index)
    if below == above:
        return ordered[below]

    # Interpolate from whichever endpoint is nearer, which is what numpy does: the single
    # `low + span * fraction` form loses the upper endpoint exactly at fraction 1.0 for large
    # spans, so approaching each endpoint from its own side is what keeps the two agreeing.
    low, high = ordered[below], ordered[above]
    span = high - low
    fraction = virtual_index - below
    if fraction < 0.5:
        return low + span * fraction
    return high - span * (1.0 - fraction)
