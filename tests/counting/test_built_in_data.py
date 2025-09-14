import pytest

from counted_float._core.counting._builtin_data import BuiltInData, _flat_to_nested_dict
from counted_float._core.counting.models import FlopsBenchmarkResults, FlopWeights, InstructionLatencies


# =================================================================================================
#  Benchmarks
# =================================================================================================
def test_builtin_data_benchmarks():
    # --- act ---------------------------------------------
    result = BuiltInData.benchmarks()

    # --- assert ------------------------------------------
    assert all(isinstance(v, FlopsBenchmarkResults) for v in result.values())
    assert len(result) == 3  # update as we add data


# =================================================================================================
#  Specs
# =================================================================================================
def test_builtin_data_specs():
    # --- act ---------------------------------------------
    result = BuiltInData.specs()

    # --- assert ------------------------------------------
    assert all(isinstance(v, InstructionLatencies) for v in result.values())
    assert len(result) == 6  # update as we add data


# =================================================================================================
#  FlopWeights
# =================================================================================================
@pytest.mark.parametrize("key_filter", [".", "specs.", "benchmarks.", "arm", "x86"])
def test_builtin_data_get_flop_weights(key_filter: str):
    # --- act ---------------------------------------------
    result = BuiltInData.get_flop_weights(key_filter=key_filter)

    # --- assert ------------------------------------------
    assert isinstance(result, FlopWeights)


def test_builtin_data_get_flop_weights_invalid_key():
    # --- arrange -----------------------------------------
    key_filter = "my_kitchen_sink"

    # --- act / assert ------------------------------------
    with pytest.raises(ValueError):
        BuiltInData.get_flop_weights(key_filter=key_filter)


@pytest.mark.parametrize(
    "key_filter, n_expected",
    [
        (".", 9),
        ("specs.", 6),
        ("benchmarks.", 3),
        ("arm", 1),
        ("x86", 8),
    ],
)
def test_builtin_data_get_flop_weights_dict(key_filter: str, n_expected: int):
    # --- arrange -----------------------------------------
    full_dict = BuiltInData.get_flop_weights_dict()

    # --- act ---------------------------------------------
    results = BuiltInData.get_flop_weights_dict(key_filter=key_filter)

    # --- assert ------------------------------------------
    assert len(results) == n_expected
    assert all(key in full_dict.keys() for key in results.keys())


# =================================================================================================
#  Helpers
# =================================================================================================
def test_builtin_data_flat_to_nested_dict():
    # --- arrange -----------------------------------------
    flat_dict = {
        "a.b.c": 1,
        "a.b.d": 2,
        "a.e": 3,
        "f": 4,
    }
    expected_nested_dict = {
        "a": {
            "b": {
                "c": 1,
                "d": 2,
            },
            "e": 3,
        },
        "f": 4,
    }

    # --- act ---------------------------------------------
    nested_dict = _flat_to_nested_dict(flat_dict)

    # --- assert ------------------------------------------
    assert nested_dict == expected_nested_dict
