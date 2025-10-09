from functools import cache
from typing import Literal

from counted_float._core.counting._builtin_data import BuiltInData
from counted_float._core.models import FlopWeights


@cache
def get_default_consensus_flop_weights(rounding_mode: None | Literal["nearest_int", "10%"] = "10%") -> FlopWeights:
    """
    Get the default CONSENSUS flop weights.
    Computed as the geo-mean of the unrounded empirical and theoretical weights, rounded to the nearest integer.
    """
    return get_builtin_flop_weights(key_filter="", rounding_mode=rounding_mode)


@cache
def get_builtin_flop_weights(
    key_filter: str = "",
    rounding_mode: None | Literal["nearest_int", "10%"] = "10%",
) -> FlopWeights:
    """
    Get built-in flop weights estimated from built-in benchmark results and/or instruction latency analyses.

    :param key_filter: (str, default="") If non-empty, only include entries whose keys contain this substring.
                       E.g. "benchmarks" to only include benchmark results, or "x86" to only include
                       x86-related flop weights.
    :param rounding_mode: (str, default="10%") rounding mode (None, "nearest_int", "10%").
    :return: A FlopWeights instance computed as the (hierarchical) geo-mean of all matching built-in data.
    :raises ValueError: If no built-in data matches the given key_filter.
    """
    weights = BuiltInData.get_flop_weights(key_filter=key_filter)
    if rounding_mode is not None:
        return weights.round(mode=rounding_mode)
    else:
        return weights
