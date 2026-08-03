import itertools
import math

import pytest

from counted_float._core.counting import CountedFloat, FlopCountingContext
from counted_float._core.evaluation import _per_flop_overhead
from counted_float._core.evaluation._per_flop_overhead import (
    PerFlopTypeLoop,
    excluded_flop_types,
    per_flop_type_specs,
)
from counted_float._core.models import FlopType

# Parametrize over the enum, not over per_flop_type_specs(): a collection-time builder call runs
# outside any test, where mutation testing cannot attribute the registry construction to the tests
# that depend on it. Every test below builds the specs inside its own body instead.
_ALL_FLOP_TYPES = list(FlopType)

# Operand values that trigger a constant fold or strength reduction somewhere in the counting
# rules; the module promises its pools never contain any of them.
_FOLD_TRIGGERS = {0.0, 1.0, -1.0}


# =================================================================================================
#  Helpers
# =================================================================================================
def _spec_for(flop_type: FlopType):
    """The loop spec for flop_type, skipping the test when it has no standalone loop here."""
    excluded = excluded_flop_types()
    if flop_type in excluded:
        pytest.skip(f"no standalone loop: {excluded[flop_type]}")
    return next(spec for spec in per_flop_type_specs() if spec.flop_type is flop_type)


def _total_count(counts) -> int:
    return sum(getattr(counts, flop_type.name) for flop_type in FlopType)


def _operand_columns(pool) -> list[list]:
    """The pool's operand streams as columns, one list per operand position.

    Handles every element schema the pools use: single operands, operand tuples, pairs of
    2-element points, and (constructor, int) pairs -- for the latter only the int stream is a
    column; the constructors are checked separately.
    """
    first = pool[0]
    if isinstance(first, tuple) and isinstance(first[0], tuple):
        return [[element[i][j] for element in pool] for i in (0, 1) for j in (0, 1)]
    if isinstance(first, tuple) and isinstance(first[0], type):
        return [[element[1] for element in pool]]
    if isinstance(first, tuple):
        return [[element[i] for element in pool] for i in range(len(first))]
    return [list(pool)]


def _measured_operands(pool) -> list:
    """The stream of measured operands: the wrapped-or-not position of each pool element."""
    first = pool[0]
    if isinstance(first, tuple) and isinstance(first[0], tuple):
        return [element[0][0] for element in pool]
    if isinstance(first, tuple) and isinstance(first[0], type):
        return [element[0] for element in pool]  # the constructor plays the measured role
    if isinstance(first, tuple):
        return [element[0] for element in pool]
    return list(pool)


# =================================================================================================
#  Registry partition
# =================================================================================================
def test_every_flop_type_is_measured_or_excluded():
    # --- arrange ----------------------
    measured = {spec.flop_type for spec in per_flop_type_specs()}
    excluded = set(excluded_flop_types())

    # --- assert -----------------------
    assert measured | excluded == set(FlopType)
    assert measured & excluded == set()


def test_every_exclusion_states_a_reason():
    assert all(reason.strip() for reason in excluded_flop_types().values())


def test_missing_math_functions_are_excluded_with_reasons(monkeypatch):
    # --- arrange ----------------------
    monkeypatch.delattr(math, "fma", raising=False)
    monkeypatch.delattr(math, "sumprod", raising=False)

    # --- act --------------------------
    excluded = excluded_flop_types()

    # --- assert -----------------------
    assert "math.fma" in excluded[FlopType.FMA]
    assert "3.13" in excluded[FlopType.FMA]
    assert "math.sumprod" in excluded[FlopType.SUMPROD]
    assert "3.12" in excluded[FlopType.SUMPROD]


def test_builders_return_fresh_objects_per_call():
    # callers may filter or annotate their copy without corrupting anyone else's
    # --- act / assert -----------------
    assert per_flop_type_specs() is not per_flop_type_specs()
    assert excluded_flop_types() is not excluded_flop_types()


# =================================================================================================
#  Per-type loops and pools
# =================================================================================================
@pytest.mark.parametrize("flop_type", _ALL_FLOP_TYPES, ids=lambda flop_type: flop_type.name)
def test_counted_loop_counts_exactly_its_flop_type(flop_type):
    # the operand pools must keep every loop on the generic counting path: one count of the
    # target type per pool element, and no fold, strength reduction, or side count of any kind
    # --- arrange ----------------------
    spec = _spec_for(flop_type)
    pool = spec.make_pool(True)

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        spec.loop(pool)
    counts = ctx.flop_counts()

    # --- assert -----------------------
    assert getattr(counts, spec.flop_type.name) == len(pool)
    assert _total_count(counts) == len(pool)


@pytest.mark.parametrize("flop_type", _ALL_FLOP_TYPES, ids=lambda flop_type: flop_type.name)
def test_float_baseline_loop_counts_nothing(flop_type):
    # the float variant must stay entirely uncounted, even with the patched math active
    # --- arrange ----------------------
    spec = _spec_for(flop_type)
    pool = spec.make_pool(False)

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        spec.loop(pool)

    # --- assert -----------------------
    assert _total_count(ctx.flop_counts()) == 0


@pytest.mark.parametrize("flop_type", _ALL_FLOP_TYPES, ids=lambda flop_type: flop_type.name)
def test_pools_are_full_sized_spread_and_fold_safe(flop_type):
    # the invariants the module docstring promises of every pool: full size, genuinely varied
    # operands (a collapsed spread would time a constant-input loop), no fold-trigger values,
    # and the measured position -- only that position -- wrapped in the counted variant
    # --- arrange ----------------------
    spec = _spec_for(flop_type)
    pool_counted = spec.make_pool(True)
    pool_plain = spec.make_pool(False)

    # --- act --------------------------
    columns = _operand_columns(pool_plain)
    measured_counted = _measured_operands(pool_counted)
    measured_plain = _measured_operands(pool_plain)

    # --- assert -----------------------
    assert len(pool_counted) == len(pool_plain) == _per_flop_overhead._POOL_SIZE
    for column in columns:
        assert all(a < b for a, b in itertools.pairwise(column))
        assert all(float(value) not in _FOLD_TRIGGERS for value in column)
    if flop_type is FlopType.I2F:
        assert all(constructor is CountedFloat for constructor in measured_counted)
        assert all(constructor is float for constructor in measured_plain)
    else:
        assert all(isinstance(value, CountedFloat) for value in measured_counted)
        assert not any(isinstance(value, CountedFloat) for value in measured_plain)


@pytest.mark.parametrize("flop_type", _ALL_FLOP_TYPES, ids=lambda flop_type: flop_type.name)
def test_the_expression_column_states_the_measured_operation(flop_type):
    # the report's expression column must be the operation the loop actually times: evaluating
    # it on one pool element registers exactly one count of exactly this flop type
    # --- arrange ----------------------
    spec = _spec_for(flop_type)
    if flop_type is FlopType.I2F:
        pytest.skip("its expression contrasts the two constructor spellings; not a single expression")
    element = spec.make_pool(True)[0]
    match element:
        case ((_, _), (_, _)):
            names = {"p": element[0], "q": element[1]}
        case (x, y, z):
            names = {"x": x, "y": y, "z": z}
        case (x, y):
            names = {"x": x, "y": y}
        case x:
            names = {"x": x}

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        eval(  # noqa: S307 -- expressions come from the registry under test, not from user input
            spec.expression, {"math": math, "__builtins__": {"abs": abs, "round": round, "int": int}}, names
        )
    counts = ctx.flop_counts()

    # --- assert -----------------------
    assert getattr(counts, flop_type.name) == 1
    assert _total_count(counts) == 1


# =================================================================================================
#  PerFlopTypeLoop
# =================================================================================================
def test_per_flop_type_loop_runs_the_requested_passes():
    # --- arrange ----------------------
    passes = []
    pool = [1.7, 2.3]
    loop = PerFlopTypeLoop(name="probe", loop=passes.append, pool=pool, in_counting_context=False)

    # --- act / assert -----------------
    loop._run_benchmark()
    assert passes == [pool]  # a fresh loop defaults to a single pass

    passes.clear()
    loop._prepare_benchmark(3)
    loop._run_benchmark()
    assert passes == [pool, pool, pool]

    assert loop.name == "probe"
    assert loop.single_execution == "pass"  # the unit named in printed per-run timings


def test_per_flop_type_loop_counts_only_in_the_counted_variant():
    # --- arrange ----------------------
    spec = _spec_for(FlopType.ADD)
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
