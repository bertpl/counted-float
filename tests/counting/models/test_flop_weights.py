import pytest

from counted_float._core.counting.models._flop_type import FlopType
from counted_float._core.counting.models._flop_weights import FlopWeights


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
    if use_dict_by_str:
        weights_dict = sample_flop_weights_dict_by_str
    else:
        weights_dict = sample_flop_weights_dict_by_enum

    # --- act ---------------------------------------------
    flop_weights = FlopWeights(weights=weights_dict)

    # --- assert ------------------------------------------

    # check if result is correct
    assert all([isinstance(k, FlopType) for k in flop_weights.weights.keys()])
    assert set(FlopType) == set(flop_weights.weights.keys())


def test_flop_weights_serialization(sample_flop_weights_dict_by_str):
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights=sample_flop_weights_dict_by_str)

    # --- act ---------------------------------------------
    result = flop_weights.model_dump()

    # --- assert ------------------------------------------
    assert result == dict(weights=sample_flop_weights_dict_by_str)
    assert not any([isinstance(k, FlopType) for k in result["weights"].keys()]), "keys should be pure strings"


@pytest.mark.parametrize("use_dict_by_str", [True, False])
def test_flop_weights_incorrect_construction(
    sample_flop_weights_dict_by_enum, sample_flop_weights_dict_by_str, use_dict_by_str: bool
) -> None:
    # --- arrange -----------------------------------------
    if use_dict_by_str:
        weights_dict = sample_flop_weights_dict_by_str
    else:
        weights_dict = sample_flop_weights_dict_by_enum

    # remove 1 key to trigger ValueError
    del weights_dict[FlopType.ABS]

    # --- act ---------------------------------------------
    with pytest.raises(ValueError):
        _ = FlopWeights(weights=weights_dict)


def test_flop_weights_print(sample_flop_weights_dict_by_str):
    """Very minimal test to check if MyBaseModel.print() at least does not raise exceptions."""
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights=sample_flop_weights_dict_by_str)

    # --- act ---------------------------------------------
    flop_weights.print()
