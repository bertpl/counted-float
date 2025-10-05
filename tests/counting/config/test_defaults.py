import math

import pytest

from counted_float._core.counting.config._defaults import get_default_consensus_flop_weights
from counted_float._core.models import FlopWeights


@pytest.mark.parametrize("rounded", [True, False])
def test_default_flop_weights(rounded: bool):
    # --- act ---------------------------------------------
    flop_weights = get_default_consensus_flop_weights(rounded=rounded)

    # --- assert ------------------------------------------
    assert isinstance(flop_weights, FlopWeights)
    assert all([isinstance(v, int | float) for v in flop_weights.weights.values()])
    assert not any([math.isnan(v) for v in flop_weights.weights.values()])


def test_default_flop_weights_rounding():
    # --- act ---------------------------------------------
    unrounded = get_default_consensus_flop_weights(rounded=False)
    rounded = get_default_consensus_flop_weights(rounded=True)

    # --- assert ------------------------------------------
    assert rounded.weights == unrounded.round().weights
