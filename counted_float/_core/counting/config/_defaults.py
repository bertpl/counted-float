from functools import cache

from counted_float._core.counting._builtin_data import BuiltInData

from ..models import FlopWeights


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
