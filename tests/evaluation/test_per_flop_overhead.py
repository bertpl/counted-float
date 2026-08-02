import pytest

from counted_float._core.counting import FlopCountingContext
from counted_float._core.evaluation._per_flop_overhead import (
    EXCLUDED_FLOP_TYPES,
    PER_FLOP_TYPE_SPECS,
)
from counted_float._core.models import FlopType


def _total_count(counts) -> int:
    return sum(getattr(counts, flop_type.name) for flop_type in FlopType)


def test_every_flop_type_is_measured_or_excluded():
    # --- arrange ----------------------
    measured = {spec.flop_type for spec in PER_FLOP_TYPE_SPECS}
    excluded = set(EXCLUDED_FLOP_TYPES)

    # --- assert -----------------------
    assert measured | excluded == set(FlopType)
    assert measured & excluded == set()


def test_every_exclusion_states_a_reason():
    assert all(reason.strip() for reason in EXCLUDED_FLOP_TYPES.values())


@pytest.mark.parametrize("spec", PER_FLOP_TYPE_SPECS, ids=lambda spec: spec.flop_type.name)
def test_counted_loop_counts_exactly_its_flop_type(spec):
    # the operand pools must keep every loop on the generic counting path: one count of the
    # target type per pool element, and no fold, strength reduction, or side count of any kind
    # --- arrange ----------------------
    pool = spec.make_pool(True)

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        spec.loop(pool)
    counts = ctx.flop_counts()

    # --- assert -----------------------
    assert getattr(counts, spec.flop_type.name) == len(pool)
    assert _total_count(counts) == len(pool)


@pytest.mark.parametrize("spec", PER_FLOP_TYPE_SPECS, ids=lambda spec: spec.flop_type.name)
def test_float_baseline_loop_counts_nothing(spec):
    # the float variant must stay entirely uncounted, even with the patched math active
    # --- arrange ----------------------
    pool = spec.make_pool(False)

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        spec.loop(pool)

    # --- assert -----------------------
    assert _total_count(ctx.flop_counts()) == 0
