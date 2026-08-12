import math

import pytest

from counted_float._core.counting.config.defaults import get_builtin_flop_weights, get_default_consensus_flop_weights
from counted_float._core.models import FlopType, FlopWeights


@pytest.mark.parametrize("rounding_mode", [None, "nearest_int", "10%"])
def test_default_flop_weights(rounding_mode: str | None):
    # --- act ---------------------------------------------
    flop_weights = get_default_consensus_flop_weights(rounding_mode=rounding_mode)

    # --- assert ------------------------------------------
    assert isinstance(flop_weights, FlopWeights)
    assert all(isinstance(v, int | float) for v in flop_weights.weights.values())
    # the re-collected dataset ships a real weight for every measured flop type
    assert not any(math.isnan(w) for w in flop_weights.weights.values())


@pytest.mark.parametrize("rounding_mode", ["nearest_int", "10%"])
def test_default_flop_weights_rounding(rounding_mode: str):
    # --- act ---------------------------------------------
    unrounded = get_default_consensus_flop_weights(rounding_mode=None)
    rounded = get_default_consensus_flop_weights(rounding_mode=rounding_mode)

    # --- assert ------------------------------------------
    assert rounded.weights == unrounded.round(rounding_mode).weights


@pytest.mark.parametrize("getter", [get_builtin_flop_weights, get_default_consensus_flop_weights])
def test_default_rounding_mode_is_ten_percent(getter):
    # the documented public default is "10%"; every other test passes rounding_mode explicitly, so
    # a changed default would slip through. Pin it: the no-arg result must match the explicit "10%"
    # result (which also rules out a nearest_int default) and differ from the unrounded (None) one.
    # --- act ---------------------------------------------
    default = getter()
    explicit_ten_percent = getter(rounding_mode="10%")
    unrounded = getter(rounding_mode=None)

    # --- assert ------------------------------------------
    assert default.weights == explicit_ten_percent.weights  # default rounds the "10%" way...
    assert default.weights != unrounded.weights  # ...and is not the unrounded default


@pytest.mark.parametrize("getter", [get_builtin_flop_weights, get_default_consensus_flop_weights])
def test_builtin_flop_weight_getters_return_defensive_copies(getter):
    # --- act ---------------------------------------------
    flop_weights = getter()
    flop_weights.weights[FlopType.ADD] = -12345.0  # mutate the returned object

    # --- assert ------------------------------------------
    assert getter().weights[FlopType.ADD] != -12345.0
