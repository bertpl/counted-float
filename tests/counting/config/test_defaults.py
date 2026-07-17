import math

import pytest

from counted_float._core.counting.config._defaults import get_builtin_flop_weights, get_default_consensus_flop_weights
from counted_float._core.models import FlopType, FlopWeights

# these flop types are measured by the benchmark suite but have no weight in any shipped source
# yet (their kernels postdate the current dataset), so they are legitimately missing from the
# default consensus until the dataset is re-collected
_PENDING_DATA = {FlopType.HYPOT_XARG, FlopType.DIST, FlopType.DIST_XARG}


@pytest.mark.parametrize("rounding_mode", [None, "nearest_int", "10%"])
def test_default_flop_weights(rounding_mode: None | str):
    # --- act ---------------------------------------------
    flop_weights = get_default_consensus_flop_weights(rounding_mode=rounding_mode)

    # --- assert ------------------------------------------
    assert isinstance(flop_weights, FlopWeights)
    assert all(isinstance(v, int | float) for v in flop_weights.weights.values())
    established = [w for ft, w in flop_weights.weights.items() if ft not in _PENDING_DATA]
    assert not any(math.isnan(w) for w in established)
    assert all(math.isnan(flop_weights.weights[ft]) for ft in _PENDING_DATA), "expected pending types missing"


@pytest.mark.parametrize("rounding_mode", ["nearest_int", "10%"])
def test_default_flop_weights_rounding(rounding_mode: str):
    # --- act ---------------------------------------------
    unrounded = get_default_consensus_flop_weights(rounding_mode=None)
    rounded = get_default_consensus_flop_weights(rounding_mode=rounding_mode)

    # --- assert ------------------------------------------
    assert rounded.weights == unrounded.round(rounding_mode).weights


@pytest.mark.parametrize("getter", [get_builtin_flop_weights, get_default_consensus_flop_weights])
def test_builtin_flop_weight_getters_return_defensive_copies(getter):
    # --- act ---------------------------------------------
    flop_weights = getter()
    flop_weights.weights[FlopType.ADD] = -12345.0  # mutate the returned object

    # --- assert ------------------------------------------
    assert getter().weights[FlopType.ADD] != -12345.0
