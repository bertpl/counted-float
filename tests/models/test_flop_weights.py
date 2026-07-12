import math

import pytest

from counted_float._core.counting.config import get_builtin_flop_weights
from counted_float._core.models import FlopType, FlopWeights


@pytest.fixture
def sample_flop_weights_dict_by_enum() -> dict[FlopType, int]:
    # return {FlopType(flop_type): i for i, flop_type in enumerate(FlopType, start=1)}
    return {flop_type: i for i, flop_type in enumerate(FlopType, start=1)}


@pytest.fixture
def sample_flop_weights_dict_by_str(sample_flop_weights_dict_by_enum) -> dict[str, int]:
    return {k.value: v for k, v in sample_flop_weights_dict_by_enum.items()}


@pytest.mark.parametrize("use_dict_by_str", [True, False])
def test_flop_weights_construction(
    sample_flop_weights_dict_by_enum, sample_flop_weights_dict_by_str, use_dict_by_str: bool
) -> None:
    # --- arrange -----------------------------------------
    weights_dict = sample_flop_weights_dict_by_str if use_dict_by_str else sample_flop_weights_dict_by_enum

    # --- act ---------------------------------------------
    flop_weights = FlopWeights(weights=weights_dict)

    # --- assert ------------------------------------------

    # check if result is correct
    assert all(isinstance(k, FlopType) for k in flop_weights.weights)
    assert set(FlopType) == set(flop_weights.weights.keys())


@pytest.mark.parametrize("has_missing_data", [True, False])
def test_flop_weights_has_missing_data(sample_flop_weights_dict_by_enum, has_missing_data: bool):
    # --- arrange -----------------------------------------
    weights_dict = sample_flop_weights_dict_by_enum
    if has_missing_data:
        weights_dict[FlopType.SQRT] = math.nan  # introduce missing data

    flop_weights = FlopWeights(weights=weights_dict)

    # --- act ---------------------------------------------
    flag = flop_weights.has_missing_data()

    # --- assert ------------------------------------------
    assert flag == has_missing_data


def test_get_sorted_flop_types_orders_by_weight_with_nan_last():
    # --- arrange -----------------------------------------
    weights = FlopWeights(
        weights={FlopType.MUL: 3.0, FlopType.ADD: 1.0, FlopType.DIV: 5.0}
    )  # every other type defaults to NaN via the validator

    # --- act ---------------------------------------------
    ordered = weights.get_sorted_flop_types()

    # --- assert ------------------------------------------
    finite = [ft for ft in ordered if not math.isnan(weights.weights[ft])]
    missing = [ft for ft in ordered if math.isnan(weights.weights[ft])]

    assert finite == [FlopType.ADD, FlopType.MUL, FlopType.DIV]  # finite weights first, ascending
    assert ordered[: len(finite)] == finite  # ...and all before the NaN block
    assert missing == sorted(missing, key=lambda ft: ft.value)  # NaN block is deterministically ordered


def test_flop_weights_serialization(sample_flop_weights_dict_by_str):
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights=sample_flop_weights_dict_by_str)

    # --- act ---------------------------------------------
    result = flop_weights.model_dump()

    # --- assert ------------------------------------------
    assert result == {"weights": sample_flop_weights_dict_by_str}
    assert not any(isinstance(k, FlopType) for k in result["weights"]), "keys should be pure strings"


@pytest.mark.parametrize("use_dict_by_str", [True, False])
def test_flop_weights_missing_flop_types(
    sample_flop_weights_dict_by_enum, sample_flop_weights_dict_by_str, use_dict_by_str: bool
) -> None:
    # --- arrange -----------------------------------------
    weights_dict = sample_flop_weights_dict_by_str if use_dict_by_str else sample_flop_weights_dict_by_enum

    # remove 1 key to trigger ValueError
    del weights_dict[FlopType.ABS]

    # --- act ---------------------------------------------
    flop_weights = FlopWeights(weights=weights_dict)
    assert math.isnan(flop_weights.weights[FlopType.ABS])


def test_flop_weights_show_smoke(sample_flop_weights_dict_by_str):
    """Very minimal test to check if MyBaseModel.print() at least does not raise exceptions."""
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights=sample_flop_weights_dict_by_str)

    # --- act ---------------------------------------------
    flop_weights.show()


@pytest.mark.parametrize("fill_missing_data", [True, False])
def test_flop_weights_as_geo_mean(sample_flop_weights_dict_by_enum, fill_missing_data: bool):
    # --- arrange -----------------------------------------
    weights1 = FlopWeights(weights=sample_flop_weights_dict_by_enum)

    weights2_dict = {k: v + 1 for k, v in sample_flop_weights_dict_by_enum.items()}
    weights2 = FlopWeights(weights=weights2_dict)

    # --- act ---------------------------------------------
    geo_mean_weights = FlopWeights.as_geo_mean(
        all_flop_weights=[weights1, weights2],
        fill_missing_data=fill_missing_data,  # there is no missing data, so should not have any effect
    )

    # --- assert ------------------------------------------
    for flop_type in FlopType:
        expected = math.sqrt(weights1.weights[flop_type] * weights2.weights[flop_type])
        assert math.isclose(geo_mean_weights.weights[flop_type], expected, rel_tol=1e-15, abs_tol=1e-15)


@pytest.mark.parametrize("rounding_mode", [None, "nearest_int", "10%"])
@pytest.mark.parametrize("key_filter", ["", "benchmark", "spec"])
def test_flop_weights_show(key_filter: str, rounding_mode: None | str):
    # make sure FlopWeights.show() doesn't raise exceptions, for int/float and with/without nan values

    # --- arrange -----------------------------------------
    flop_weights = get_builtin_flop_weights(key_filter, rounding_mode)

    # --- act & assert ------------------------------------
    flop_weights.show()
