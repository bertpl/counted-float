import math


def geo_mean(values: list[float | int]) -> float:
    """Take geometric mean of list of values, returning None if any value is None or list is empty."""
    if len(values) == 0:
        return 0.0
    else:
        return pow(math.prod(values), 1 / len(values))
