import math


def geo_mean(values: list[float | int]) -> float:
    """Take geometric mean of list of values, returning 0.0 for an empty list.

    nan values propagate (nan in -> nan out).
    """
    if len(values) == 0:
        return 0.0
    return pow(math.prod(values), 1 / len(values))
