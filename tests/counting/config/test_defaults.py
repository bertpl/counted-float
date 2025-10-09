import math

import pytest

from counted_float._core.counting.config._defaults import get_default_consensus_flop_weights
from counted_float._core.models import FlopWeights


@pytest.mark.parametrize("rounding_mode", [None, "nearest_int", "10%"])
def test_default_flop_weights(rounding_mode: None | str):
    # --- act ---------------------------------------------
    flop_weights = get_default_consensus_flop_weights(rounding_mode=rounding_mode)

    # --- assert ------------------------------------------
    assert isinstance(flop_weights, FlopWeights)
    assert all([isinstance(v, int | float) for v in flop_weights.weights.values()])
    assert not any([math.isnan(v) for v in flop_weights.weights.values()])


@pytest.mark.parametrize("rounding_mode", ["nearest_int", "10%"])
def test_default_flop_weights_rounding(rounding_mode: str):
    # --- act ---------------------------------------------
    unrounded = get_default_consensus_flop_weights(rounding_mode=None)
    rounded = get_default_consensus_flop_weights(rounding_mode=rounding_mode)

    # --- assert ------------------------------------------
    assert rounded.weights == unrounded.round(rounding_mode).weights
