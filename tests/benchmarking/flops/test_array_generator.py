import random
from collections.abc import Callable

import numpy as np
import pytest

from counted_float._core.benchmarking.flops._array_generator import (
    ArrayGenerator,
    ArrayGeneratorLinear,
    ArrayGeneratorLog,
    _random_balanced_values,
)


@pytest.mark.parametrize(
    ("factory_method", "expected_cls"),
    [
        (ArrayGenerator.lin_range, ArrayGeneratorLinear),
        (ArrayGenerator.log_range, ArrayGeneratorLog),
    ],
)
def test_array_generator_factory_methods(factory_method: Callable, expected_cls):
    # --- act ---------------------------------------------
    generator = factory_method(min_value=0.1, max_value=10.0)

    # --- assert ------------------------------------------
    assert isinstance(generator, ArrayGenerator)
    assert isinstance(generator, expected_cls)
    assert generator.min_value == 0.1
    assert generator.max_value == 10.0


@pytest.mark.parametrize(
    ("min_value", "max_value"),
    [
        (0.0, 1.0),
        (-2.0, 10.0),
        (100.0, 1000.0),
    ],
)
def test_array_generator_linear(min_value: float, max_value: float):
    # --- arrange -----------------------------------------
    generator = ArrayGeneratorLinear(min_value=min_value, max_value=max_value)

    # --- act ---------------------------------------------
    arr = generator.new_array(size=1000)

    # --- assert ------------------------------------------
    assert all(min_value <= v <= max_value for v in arr)
    assert len(set(arr)) == 1000
    assert min_value < np.mean(arr) < max_value
    assert np.mean(arr) == pytest.approx(0.5 * (min_value + max_value))
    assert max(arr) - min(arr) > 0.9 * (max_value - min_value)


@pytest.mark.parametrize(
    ("min_value", "max_value"),
    [
        (0.1, 1.0),
        (2.0, 10.0),
        (100.0, 1000.0),
    ],
)
def test_array_generator_log(min_value: float, max_value: float):
    # --- arrange -----------------------------------------
    generator = ArrayGeneratorLog(min_value=min_value, max_value=max_value)

    # --- act ---------------------------------------------
    arr = generator.new_array(size=1000)

    # --- assert ------------------------------------------
    assert all(min_value <= v <= max_value for v in arr)
    assert len(set(arr)) == 1000
    assert min_value < np.mean(arr) < max_value
    assert np.mean(np.log(arr)) == pytest.approx(0.5 * (np.log(min_value) + np.log(max_value)))
    assert max(arr) - min(arr) > 0.9 * (max_value - min_value)


def test_new_array_is_reproducible_when_given_a_seeded_rng():
    """Passing a seeded rng makes new_array deterministic; a different seed changes the draw."""
    # --- arrange -----------------------------------------
    generator = ArrayGeneratorLinear(min_value=0.0, max_value=1.0)

    # --- act ---------------------------------------------
    first = generator.new_array(size=500, rng=random.Random(12345))
    second = generator.new_array(size=500, rng=random.Random(12345))
    different_seed = generator.new_array(size=500, rng=random.Random(67890))

    # --- assert ------------------------------------------
    np.testing.assert_array_equal(first, second)  # same seed -> identical draw (rng is honored)
    assert not np.array_equal(first, different_seed)  # different seed -> different draw


@pytest.mark.parametrize("seed", [0, 7, 12345])
@pytest.mark.parametrize("size", [2, 10, 1000])
def test_random_balanced_values_invariants_before_scaling(size: int, seed: int):
    """Pre-scaling contract: values in [-1,1], every partial sum in [-1,1], exact zero total."""
    # --- arrange -----------------------------------------
    tol = 1e-9  # allows only float rounding, not a broken clamp (which drifts by O(size))

    # --- act ---------------------------------------------
    values = _random_balanced_values(size, rng=random.Random(seed))

    # --- assert ------------------------------------------
    assert len(values) == size
    partial = 0.0
    for v in values:
        assert -1.0 <= v <= 1.0  # each draw stays in [-1, 1]
        partial += v
        assert -1.0 - tol <= partial <= 1.0 + tol  # the clamp keeps every partial sum bounded
    assert partial == 0.0  # the final element drives the running total exactly to zero
