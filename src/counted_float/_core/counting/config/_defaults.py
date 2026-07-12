import math
from functools import cache
from typing import Literal

from counted_float._core.counting._builtin_data import BuiltInData
from counted_float._core.models import FlopType, FlopWeights

# =================================================================================================
#  TEMPORARY placeholder weights
# =================================================================================================
# The higher-order libm ops below have no measured data yet: they have no hardware instruction
# (so no spec-sheet latency), and their benchmark kernels + measurements only arrive with the
# built-in dataset refresh. Until then their consensus weight is NaN, which poisons any
# total_weighted_cost that mixes them with real ops (0 * nan == nan).
#
# These placeholders are order-of-magnitude estimates by analogy with the nearest measured op,
# so that weighted counting returns sane values in the interim. They are applied ONLY to the
# specific types listed here and ONLY where the real weight is still NaN, so any *other* type
# that unexpectedly goes missing still surfaces loudly as NaN.
#
# >>> REMOVE this block (and _fill_placeholder_weights) once the dataset refresh provides real,
# >>> measured weights for these operations. It exists solely to bridge the gap between adding the
# >>> new FLOP types and collecting their benchmark data.
_PLACEHOLDER_WEIGHTS: dict[FlopType, float] = {
    FlopType.ASIN: 30.0,  # ~ SIN / COS
    FlopType.ACOS: 30.0,  # ~ SIN / COS
    FlopType.ATAN: 30.0,  # ~ SIN / COS
    FlopType.ATAN2: 45.0,  # atan + div + quadrant selection
    FlopType.HYPOT: 12.0,  # overflow-safe sqrt path, pricier than a raw SQRT
    FlopType.EXPM1: 18.0,  # ~ EXP
    FlopType.LOG1P: 18.0,  # ~ LOG
    FlopType.FMOD: 8.0,  # ~ DIV plus a few ops
}


def _fill_placeholder_weights(weights: FlopWeights) -> FlopWeights:
    """Fill placeholder weights for the not-yet-measured higher-order libm ops.

    TEMPORARY: remove once the dataset refresh provides real measured weights for these types
    (see `_PLACEHOLDER_WEIGHTS` above). Only fills a placeholder where the current weight is NaN,
    and only for the specific ops in `_PLACEHOLDER_WEIGHTS`, so any other missing weight still
    surfaces as NaN rather than being silently masked.
    """
    filled = dict(weights.weights)
    for flop_type, placeholder in _PLACEHOLDER_WEIGHTS.items():
        if math.isnan(filled[flop_type]):
            filled[flop_type] = placeholder
    return FlopWeights(weights=filled)


# =================================================================================================
#  Public accessors
# =================================================================================================
def get_default_consensus_flop_weights(rounding_mode: None | Literal["nearest_int", "10%"] = "10%") -> FlopWeights:
    """Get the default CONSENSUS flop weights.

    Computed as the geo-mean of the unrounded empirical and theoretical weights, rounded to the nearest integer.
    Returns a fresh copy; mutating it does not affect later calls.
    """
    return get_builtin_flop_weights(key_filter="", rounding_mode=rounding_mode)


def get_builtin_flop_weights(
    key_filter: str = "",
    rounding_mode: None | Literal["nearest_int", "10%"] = "10%",
) -> FlopWeights:
    """Get built-in flop weights estimated from built-in benchmark results and/or instruction latency analyses.

    :param key_filter: (str, default="") If non-empty, only include entries whose keys contain this substring.
                       E.g. "benchmarks" to only include benchmark results, or "x86" to only include
                       x86-related flop weights.
    :param rounding_mode: (str, default="10%") rounding mode (None, "nearest_int", "10%").
    :return: A FlopWeights instance computed as the (hierarchical) geo-mean of all matching built-in data.
             A fresh copy on every call; mutating it does not corrupt the underlying cache.
    :raises ValueError: If no built-in data matches the given key_filter.
    """
    return _get_builtin_flop_weights_cached(key_filter, rounding_mode).model_copy(deep=True)


@cache
def _get_builtin_flop_weights_cached(
    key_filter: str,
    rounding_mode: None | Literal["nearest_int", "10%"],
) -> FlopWeights:
    weights = BuiltInData.get_flop_weights(key_filter=key_filter)
    weights = _fill_placeholder_weights(weights)  # TEMPORARY: remove with the dataset refresh (see above)
    if rounding_mode is not None:
        return weights.round(mode=rounding_mode)
    return weights
