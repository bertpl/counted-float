"""The shipped aggregates must stay in step with the source data they were derived from."""

import math

import pytest

from counted_float._core.counting.builtin_data.dataset import (
    _aggregate_flop_weights_from_sources,
    _precomputed_flop_weights,
)
from counted_float._core.counting.config import get_builtin_flop_weights
from counted_float._core.models import FlopType

# far below any real drift (a data change moves weights by ~1e-2), far above float noise across
# platforms (~1e-13 on weights of order 1-100), so this separates "stale" from "different runner"
DRIFT_TOLERANCE = 1e-10


@pytest.mark.parametrize("key_filter", ["", "arm", "x86"])
def test_precomputed_aggregate_matches_the_derived_one(key_filter: str):
    """Fails when the source data changed and `make precompute-weights` was not re-run."""
    # --- arrange -----------------------------------------
    precomputed = _precomputed_flop_weights()[key_filter]

    # --- act ---------------------------------------------
    derived = _aggregate_flop_weights_from_sources(key_filter)  # straight from the source tree

    # --- assert ------------------------------------------
    for flop_type in FlopType:
        stored, fresh = precomputed.weights[flop_type], derived.weights[flop_type]
        if math.isnan(fresh):
            assert math.isnan(stored), f"{key_filter or '<all>'}: {flop_type.name} is missing when derived"
        else:
            assert stored == pytest.approx(fresh, abs=DRIFT_TOLERANCE, rel=DRIFT_TOLERANCE), (
                f"{key_filter or '<all>'}: {flop_type.name} drifted -- re-run `make precompute-weights`"
            )


def test_precomputed_aggregates_are_stored_unrounded():
    """Storing them rounded would pin the cache to one rounding mode; every other mode wants these raw."""
    # --- arrange / act -----------------------------------
    precomputed = _precomputed_flop_weights()[""]

    # --- assert ------------------------------------------
    rounded = precomputed.round(mode="10%")
    assert precomputed.weights != rounded.weights, "stored aggregate looks pre-rounded"


@pytest.mark.parametrize("rounding_mode", [None, "nearest_int", "10%"])
def test_every_rounding_mode_is_served_from_the_stored_aggregate(rounding_mode):
    # --- act ---------------------------------------------
    weights = get_builtin_flop_weights("", rounding_mode)

    # --- assert ------------------------------------------
    expected = _aggregate_flop_weights_from_sources("")
    if rounding_mode is not None:
        expected = expected.round(mode=rounding_mode)
    for flop_type in FlopType:
        served, want = weights.weights[flop_type], expected.weights[flop_type]
        if math.isnan(want):
            assert math.isnan(served), f"{flop_type.name}: served a value where the aggregate is missing"
        else:
            assert served == pytest.approx(want, abs=DRIFT_TOLERANCE, rel=DRIFT_TOLERANCE)


def test_an_unprecomputed_filter_still_derives():
    """Filters nobody precomputed must fall through to the source tree, not fail."""
    # --- act ---------------------------------------------
    weights = get_builtin_flop_weights("intel", rounding_mode=None)

    # --- assert ------------------------------------------
    assert "intel" not in _precomputed_flop_weights()
    assert weights.weights[FlopType.ADD] == pytest.approx(1.0, abs=DRIFT_TOLERANCE)
