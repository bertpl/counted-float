import math

import pytest

from counted_float._core.benchmarking.flops import FlopsBenchmarkSuite, FlopsMicroBenchmark
from counted_float._core.models import FlopsBenchmarkResults, FlopsBenchmarkType, FlopType, FlopWeights


def test_flops_benchmarking_suite_get():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    benchmarks = suite.get_flops_benchmarking_suite(size=12345)

    # --- assert ------------------------------------------
    assert all(fbt in benchmarks for fbt in FlopsBenchmarkType)
    assert all(isinstance(v, FlopsMicroBenchmark) for v in benchmarks.values())
    assert all(v.size == 12345 for v in benchmarks.values())


def test_flops_benchmarking_suite_run():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    result = suite.run(
        array_size=10,
        t_slice_target_ms=0.1,
        n_rounds_measure=5,
        n_rounds_warmup=1,
        seed=42,
    )  # override defaults to keep test short

    # --- assert ------------------------------------------
    assert isinstance(result, FlopsBenchmarkResults)


# =================================================================================================
#  floor_latencies
# =================================================================================================
def _latencies(overrides: dict[FlopType, float]) -> dict[FlopType, float]:
    """Build a full latency dict with plausible defaults, then apply overrides."""
    latencies = dict.fromkeys(FlopType, 5.0)
    latencies.update(overrides)
    return latencies


def test_floor_latencies_leaves_genuine_values_untouched():
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ABS: 2.0, FlopType.POW: 150.0})

    # --- act ---------------------------------------------
    floored = FlopsBenchmarkSuite.floor_latencies(latencies)

    # --- assert ------------------------------------------
    assert floored == latencies


@pytest.mark.parametrize("bad_value", [0.0, -0.3, -100.0])
def test_floor_latencies_clamps_non_positive_values(bad_value: float):
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ABS: bad_value})

    # --- act ---------------------------------------------
    floored = FlopsBenchmarkSuite.floor_latencies(latencies)

    # --- assert ------------------------------------------
    assert floored[FlopType.ABS] == FlopsBenchmarkSuite.MIN_LATENCY_ADD_FRACTION * latencies[FlopType.ADD]
    assert all(v > 0 for v in floored.values())


def test_floor_latencies_survives_non_positive_add():
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ADD: -1.0, FlopType.ABS: -2.0})

    # --- act ---------------------------------------------
    floored = FlopsBenchmarkSuite.floor_latencies(latencies)

    # --- assert ------------------------------------------
    assert all(v > 0 for v in floored.values())


def test_floored_latencies_yield_finite_positive_weights():
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ABS: -0.5, FlopType.MINUS: 0.0})

    # --- act ---------------------------------------------
    weights = FlopWeights.from_abs_flop_costs(FlopsBenchmarkSuite.floor_latencies(latencies))

    # --- assert ------------------------------------------
    assert all(math.isfinite(w) and w > 0 for w in weights.weights.values())
