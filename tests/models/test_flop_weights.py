import json
import math

import pytest
from pydantic import ValidationError

from counted_float._core.counting import BuiltInData
from counted_float._core.counting.config import get_builtin_flop_weights
from counted_float._core.models import FlopType, FlopWeights


@pytest.fixture
def sample_flop_weights_dict_by_enum() -> dict[FlopType, int]:
    # return {FlopType(flop_type): i for i, flop_type in enumerate(FlopType, start=1)}
    return {flop_type: i for i, flop_type in enumerate(FlopType, start=1)}


@pytest.fixture
def sample_flop_weights_dict_by_str(sample_flop_weights_dict_by_enum) -> dict[str, int]:
    # serialized form keys on the stable name (== member value)
    return {k.name: v for k, v in sample_flop_weights_dict_by_enum.items()}


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
    assert missing == sorted(missing, key=lambda ft: ft.name)  # NaN block is deterministically ordered


def test_flop_weights_serialization(sample_flop_weights_dict_by_str):
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights=sample_flop_weights_dict_by_str)

    # --- act ---------------------------------------------
    result = flop_weights.model_dump()

    # --- assert ------------------------------------------
    assert result == {"weights": sample_flop_weights_dict_by_str}
    assert not any(isinstance(k, FlopType) for k in result["weights"]), "keys should be pure strings"


def test_serialized_json_keys_on_stable_names_not_labels():
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights={FlopType.ADD: 1.0, FlopType.MUL: 2.0})

    # --- act ---------------------------------------------
    on_disk = json.loads(flop_weights.model_dump_json())["weights"]

    # --- assert ------------------------------------------
    assert on_disk["ADD"] == 1.0  # stable names, not "x+y" / "x*y"
    assert on_disk["MUL"] == 2.0


def test_str_renders_human_labels():
    # the pretty (__str__/show) path passes a display context so a human sees the readable labels
    rendered = json.loads(str(FlopWeights(weights={FlopType.ADD: 1.0})))["weights"]
    assert "x+y" in rendered  # human label...
    assert "ADD" not in rendered  # ...not the stable name


def test_legacy_label_keyed_weights_raise():
    # a pre-2.0.0 file keyed weights on the display label; those files must be regenerated,
    # and the failure is loud rather than a silent degradation to missing data
    with pytest.raises(ValidationError, match="unrecognized flop-type key"):
        FlopWeights.model_validate_json('{"weights": {"x+y": 1.0, "x*y": 2.0}}')


def test_unrecognized_weight_key_raises_instead_of_becoming_missing_data():
    # a renamed/garbage key must fail loudly, not silently degrade into a NaN weight
    with pytest.raises(ValidationError, match="unrecognized flop-type key"):
        FlopWeights.model_validate_json('{"weights": {"not-a-flop-type": 1.0}}')


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
    """Very minimal test to check if show() at least does not raise exceptions."""
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights=sample_flop_weights_dict_by_str)

    # --- act ---------------------------------------------
    flop_weights.show()


@pytest.mark.parametrize(("weight", "expected"), [(0.3, 1), (2.4, 2)])
def test_round_nearest_int_floors_at_one_and_returns_int(weight: float, expected: int):
    # 0.3 would round to 0, but the max(1, ...) floor lifts it to 1; 2.4 is a normal round above
    # the floor. Both must come back as a genuine int, not a 1.0 float (the "10%"/round_number path
    # returns floats, so the type is what tells the two apart).
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights={FlopType.ADD: weight})

    # --- act ---------------------------------------------
    rounded = flop_weights.round("nearest_int").weights[FlopType.ADD]

    # --- assert ------------------------------------------
    assert rounded == expected
    assert isinstance(rounded, int)  # a genuine int...
    assert not isinstance(rounded, float)  # ...never a float (the "10%"/round_number path returns floats)


def test_round_nearest_int_leaves_missing_weights_missing():
    # a NaN weight marks "unknown"; rounding must skip it, not turn it into a number (and note that
    # round(nan) would itself raise, so a dropped NaN guard blows up here rather than degrading)
    # --- arrange -----------------------------------------
    flop_weights = FlopWeights(weights={FlopType.ADD: 2.0, FlopType.MUL: math.nan})

    # --- act ---------------------------------------------
    rounded = flop_weights.round("nearest_int")

    # --- assert ------------------------------------------
    assert rounded.weights[FlopType.ADD] == 2
    assert math.isnan(rounded.weights[FlopType.MUL])  # missing stays missing


def test_as_geo_mean_fill_missing_data_imputes_only_when_true(sample_flop_weights_dict_by_enum):
    # one genuinely missing entry makes the two branches diverge: fill=True imputes it to a finite
    # value (so the row's geo-mean is finite), fill=False leaves it NaN (so the geo-mean propagates
    # NaN). Present entries must be untouched either way.
    # --- arrange -----------------------------------------
    weights1 = FlopWeights(weights=dict(sample_flop_weights_dict_by_enum))
    weights2_dict = {k: v + 1 for k, v in sample_flop_weights_dict_by_enum.items()}
    weights2_dict[FlopType.MUL] = math.nan  # the only missing entry
    weights2 = FlopWeights(weights=weights2_dict)

    # --- act ---------------------------------------------
    filled = FlopWeights.as_geo_mean([weights1, weights2], fill_missing_data=True)
    unfilled = FlopWeights.as_geo_mean([weights1, weights2], fill_missing_data=False)

    # --- assert ------------------------------------------
    assert not math.isnan(filled.weights[FlopType.MUL])  # imputed -> finite
    assert math.isnan(unfilled.weights[FlopType.MUL])  # left missing -> NaN propagates
    assert filled.weights[FlopType.ADD] == unfilled.weights[FlopType.ADD]  # present data untouched by fill


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


def test_from_abs_flop_costs_without_add_raises_value_error():
    # --- arrange -----------------------------------------
    flop_costs = {FlopType.MUL: 1.0}

    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="reference operation"):
        FlopWeights.from_abs_flop_costs(flop_costs)


@pytest.mark.parametrize("ref_cost", [0.0, -2.0, math.nan, math.inf])
def test_from_abs_flop_costs_with_unusable_add_raises_value_error(ref_cost: float):
    # --- arrange -----------------------------------------
    flop_costs = dict.fromkeys(FlopType, 1.0)
    flop_costs[FlopType.ADD] = ref_cost

    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="finite and positive"):
        FlopWeights.from_abs_flop_costs(flop_costs)


def test_weights_with_missing_data_survive_a_json_round_trip():
    # --- arrange -----------------------------------------
    weights = FlopWeights(weights={FlopType.ADD: 1.0, FlopType.MUL: math.nan})

    # --- act ---------------------------------------------
    restored = FlopWeights.model_validate_json(weights.model_dump_json())

    # --- assert ------------------------------------------
    assert restored.weights[FlopType.ADD] == 1.0
    assert math.isnan(restored.weights[FlopType.MUL])  # missing must stay missing, not become a number


def test_every_builtin_source_survives_a_json_round_trip():
    """Every built-in per-source weight set has missing data, so all of them exercise the null path."""
    # --- arrange -----------------------------------------
    per_source_weights = BuiltInData.get_flop_weights_dict()

    # --- act / assert ------------------------------------
    for key, weights in per_source_weights.items():
        restored = FlopWeights.model_validate_json(weights.model_dump_json())
        for flop_type, weight in weights.weights.items():
            restored_weight = restored.weights[flop_type]
            if math.isnan(weight):
                assert math.isnan(restored_weight), f"{key}: {flop_type.name} lost its missing marker"
            else:
                assert restored_weight == weight, f"{key}: {flop_type.name} changed value"


@pytest.mark.parametrize("bad_cost", [-0.5, -math.inf, math.inf])
def test_from_abs_flop_costs_with_an_unusable_non_reference_cost_raises_value_error(bad_cost: float):
    # --- arrange -----------------------------------------
    flop_costs = dict.fromkeys(FlopType, 1.0)
    flop_costs[FlopType.MUL] = bad_cost

    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="finite and non-negative"):
        FlopWeights.from_abs_flop_costs(flop_costs)


@pytest.mark.parametrize(("cost", "expected"), [(0.0, 0.0), (math.nan, math.nan)])
def test_from_abs_flop_costs_accepts_a_free_or_unknown_non_reference_cost(cost: float, expected: float):
    """Zero means free and NaN means unknown; only negative and infinite costs are nonsense."""
    # --- arrange -----------------------------------------
    flop_costs = dict.fromkeys(FlopType, 1.0)
    flop_costs[FlopType.MUL] = cost

    # --- act ---------------------------------------------
    weights = FlopWeights.from_abs_flop_costs(flop_costs)

    # --- assert ------------------------------------------
    weight = weights.weights[FlopType.MUL]
    assert math.isnan(weight) if math.isnan(expected) else weight == expected


def test_show_lists_measured_weights_before_missing_ones(capsys):
    # --- arrange -----------------------------------------
    weights = dict.fromkeys(FlopType, math.nan)
    weights[FlopType.ADD] = 1.0
    weights[FlopType.MUL] = 2.0

    # --- act ---------------------------------------------
    FlopWeights(weights=weights).show()

    # --- assert ------------------------------------------
    shown = [line for line in capsys.readouterr().out.split("\n") if ":" in line]
    assert FlopType.ADD.long_name() in shown[0]
    assert FlopType.MUL.long_name() in shown[1]
