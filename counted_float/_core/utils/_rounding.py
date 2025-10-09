import math
from typing import Literal

# Values below are used in the "10%" rounding mode and are chosen such...
#  - they span the range [1.0, 10.0] end-to-end
#  - they have ±10% increments
#  - deltas are monotonically increasing and are multiples of 0.1
#  - all integers are included (2.0, 3.0, ..., 9.0)
__ALLOWED_10PERC_ROUNDING_VALUES = [
    1.0,
    1.1,  # +0.1
    1.2,  # +0.1
    1.3,  # +0.1
    1.4,  # +0.1
    1.5,  # +0.1
    1.6,  # +0.1
    1.8,  # +0.2
    2.0,  # +0.2
    2.2,  # +0.2
    2.4,  # +0.2
    2.7,  # +0.3
    3.0,  # +0.3
    3.3,  # +0.3
    3.6,  # +0.3
    4.0,  # +0.4
    4.5,  # +0.5
    5.0,  # +0.5
    5.5,  # +0.5
    6.0,  # +0.5
    6.5,  # +0.5
    7.0,  # +0.5
    7.5,  # +0.5
    8.0,  # +0.5
    9.0,  # +1.0
    10.0,  # +1.0
]


def round_number(value: float, mode: None | Literal["nearest_int", "10%"]) -> float:
    """
    Round a floating point number according to the specified mode:
        None            -> no rounding, value is returned as is
        "nearest_int"   -> round to nearest integer
        "10%"           -> round to nearest n*10^m with n in __ALLOWED_10PERC_ROUNDING_VALUES
    """
    match mode:
        case "nearest_int":
            return round(value, 0)
        case "10%":
            if value == 0:
                return 0
            elif value < 0:
                return -round_number(-value, mode)
            elif 1.0 <= value <= 10.0:
                return _round_to_log_nearest(value, __ALLOWED_10PERC_ROUNDING_VALUES)
            else:
                scale = 10 ** math.floor(math.log10(value))
                return scale * round_number(value / scale, mode)
        case _:
            return value


def _round_to_log_nearest(value: float, candidate_value: list[float]) -> float:
    """Return candidate_value that is log-closest to value, assuming all are >0."""
    log_value = math.log(value)
    return min(candidate_value, key=lambda cand: abs(math.log(cand) - log_value))
