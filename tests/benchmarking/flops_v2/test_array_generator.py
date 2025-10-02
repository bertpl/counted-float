from typing import Callable

import numpy as np
import pytest

from counted_float._core.benchmarking.flops_v2._array_generator import (
    ArrayGenerator,
    ArrayGeneratorLinear,
    ArrayGeneratorLog,
)


@pytest.mark.parametrize(
    "factory_method, expected_cls",
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
    "min_value, max_value",
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
    assert all([min_value <= v <= max_value for v in arr])
    assert len(set(arr)) == 1000
    assert min_value < np.mean(arr) < max_value
    assert np.mean(arr) == pytest.approx(0.5 * (min_value + max_value))
    assert max(arr) - min(arr) > 0.9 * (max_value - min_value)


@pytest.mark.parametrize(
    "min_value, max_value",
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
    assert all([min_value <= v <= max_value for v in arr])
    assert len(set(arr)) == 1000
    assert min_value < np.mean(arr) < max_value
    assert np.mean(np.log(arr)) == pytest.approx(0.5 * (np.log(min_value) + np.log(max_value)))
    assert max(arr) - min(arr) > 0.9 * (max_value - min_value)
