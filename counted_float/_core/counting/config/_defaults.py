from functools import cache

from counted_float._core.counting._builtin_data import BuiltInData
from counted_float._core.models import FlopWeights


@cache
def get_default_consensus_flop_weights(rounded: bool = True) -> FlopWeights:
    """
    Get the default CONSENSUS flop weights.
    Computed as the geo-mean of the unrounded empirical and theoretical weights, rounded to the nearest integer.
    """
    weights = FlopWeights.as_geo_mean(
        [
            get_default_empirical_flop_weights(rounded=False),
            get_default_theoretical_flop_weights(rounded=False),
        ]
    )
    if rounded:
        return weights.round()
    else:
        return weights


@cache
def get_default_empirical_flop_weights(rounded: bool = True) -> FlopWeights:
    """
    Get the default EMPIRICAL flop weights.
    Computed as the geo-mean of flop weights estimated from built-in benchmark results.
    """
    weights = BuiltInData.get_flop_weights(key_filter="benchmarks.")
    if rounded:
        return weights.round()
    else:
        return weights


@cache
def get_default_theoretical_flop_weights(rounded: bool = True) -> FlopWeights:
    """
    Get the default THEORETICAL flop weights.
    Computed as the geo-mean of flop weights estimated from built-in instruction latency analyse.
    """
    weights = BuiltInData.get_flop_weights(key_filter="specs.")
    if rounded:
        return weights.round()
    else:
        return weights


@cache
def get_builtin_flop_weights(key_filter: str = "") -> FlopWeights:
    """
    Get built-in flop weights estimated from built-in benchmark results and/or instruction latency analyses.

    :param key_filter: (str, default="") If non-empty, only include entries whose keys contain this substring.
                       E.g. "benchmarks" to only include benchmark results, or "x86" to only include
                       x86-related flop weights.
    :return: A FlopWeights instance computed as the (hierarchical) geo-mean of all matching built-in data.
    :raises ValueError: If no built-in data matches the given key_filter.
    """
    return BuiltInData.get_flop_weights(key_filter=key_filter)
