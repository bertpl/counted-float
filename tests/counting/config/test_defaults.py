from typing import Callable

import pytest

from counted_float._core.counting.config._defaults import (
    get_default_consensus_flop_weights,
    get_default_empirical_flop_weights,
    get_default_theoretical_flop_weights,
)
from counted_float._core.counting.models import FlopType, FlopWeights


@pytest.mark.parametrize(
    "fun",
    [
        get_default_consensus_flop_weights,
        get_default_empirical_flop_weights,
        get_default_theoretical_flop_weights,
    ],
)
@pytest.mark.parametrize("rounded", [True, False])
def test_default_flop_weights(fun: Callable, rounded: bool):
    # --- act ---------------------------------------------
    flop_weights = fun(rounded=rounded)

    # --- assert ------------------------------------------
    assert isinstance(flop_weights, FlopWeights)
    if rounded:
        assert all([isinstance(v, int) for v in flop_weights.weights.values()])
    else:
        assert all([isinstance(v, float) for v in flop_weights.weights.values()])


@pytest.mark.parametrize(
    "fun",
    [
        get_default_consensus_flop_weights,
        get_default_empirical_flop_weights,
        get_default_theoretical_flop_weights,
    ],
)
def test_default_flop_weights_rounding(fun: Callable):
    # --- act ---------------------------------------------
    unrounded = fun(rounded=False)
    rounded = fun(rounded=True)

    # --- assert ------------------------------------------
    assert rounded.weights == unrounded.round().weights


def test_consensus_flop_weights():
    # --- arrange -----------------------------------------
    fw_theoretical = get_default_theoretical_flop_weights()
    fw_empirical = get_default_empirical_flop_weights()

    # --- act ---------------------------------------------
    fw_consensus = get_default_consensus_flop_weights()

    # --- assert ------------------------------------------
    for flop_type in FlopType:
        min_value = min(fw_theoretical.weights[flop_type], fw_empirical.weights[flop_type])
        max_value = max(fw_theoretical.weights[flop_type], fw_empirical.weights[flop_type])

        assert min_value <= fw_consensus.weights[flop_type] <= max_value, (
            f"consensus for {flop_type} should be between theoretical and empirical values"
        )
