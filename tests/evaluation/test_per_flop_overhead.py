import pytest

from counted_float._core.counting import FlopCountingContext
from counted_float._core.evaluation._per_flop_overhead import (
    PerFlopTypeLoop,
    excluded_flop_types,
    per_flop_type_specs,
)
from counted_float._core.models import FlopType


def _total_count(counts) -> int:
    return sum(getattr(counts, flop_type.name) for flop_type in FlopType)


def test_every_flop_type_is_measured_or_excluded():
    # --- arrange ----------------------
    measured = {spec.flop_type for spec in per_flop_type_specs()}
    excluded = set(excluded_flop_types())

    # --- assert -----------------------
    assert measured | excluded == set(FlopType)
    assert measured & excluded == set()


def test_every_exclusion_states_a_reason():
    assert all(reason.strip() for reason in excluded_flop_types().values())


def test_per_flop_type_loop_counts_only_in_the_counted_variant():
    # --- arrange ----------------------
    spec = next(s for s in per_flop_type_specs() if s.flop_type is FlopType.ADD)
    pool_counted = spec.make_pool(True)
    loop_counted = PerFlopTypeLoop(
        name="ADD [CountedFloat]", loop=spec.loop, pool=pool_counted, in_counting_context=True
    )
    loop_float = PerFlopTypeLoop(
        name="ADD [float]", loop=spec.loop, pool=spec.make_pool(False), in_counting_context=False
    )
    loop_counted._prepare_benchmark(2)
    loop_float._prepare_benchmark(2)

    # --- act --------------------------
    with FlopCountingContext() as ctx:  # outer context: the counted variant's own context nests inside it
        loop_float._run_benchmark()
        counts_after_float = ctx.flop_counts()
        loop_counted._run_benchmark()
    counts = ctx.flop_counts()

    # --- assert -----------------------
    assert _total_count(counts_after_float) == 0  # the float variant registers nothing
    assert 2 * len(pool_counted) == counts.ADD  # n_executions passes, one ADD per pool element


def test_builders_return_fresh_objects_per_call():
    # callers may filter or annotate their copy without corrupting anyone else's
    # --- act / assert -----------------
    assert per_flop_type_specs() is not per_flop_type_specs()
    assert excluded_flop_types() is not excluded_flop_types()


@pytest.mark.parametrize("spec", per_flop_type_specs(), ids=lambda spec: spec.flop_type.name)
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


@pytest.mark.parametrize("spec", per_flop_type_specs(), ids=lambda spec: spec.flop_type.name)
def test_float_baseline_loop_counts_nothing(spec):
    # the float variant must stay entirely uncounted, even with the patched math active
    # --- arrange ----------------------
    pool = spec.make_pool(False)

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        spec.loop(pool)

    # --- assert -----------------------
    assert _total_count(ctx.flop_counts()) == 0
