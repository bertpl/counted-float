import dataclasses
import random

from counted_float import FlopWeights
from counted_float._core.counting.config import get_flop_weights
from counted_float._core.counting.models import FlopCounts, FlopType


def test_flop_counts_field_names():
    """Test if FlopCounts .field_names() is correct and identical to FlopType names."""

    # --- arrange -----------------------------------------
    flop_type_names = {flop_type.name for flop_type in FlopType}

    # --- act ---------------------------------------------
    flop_count_field_names_1 = {field.name for field in dataclasses.fields(FlopCounts)}
    flop_count_field_names_2 = set(FlopCounts.field_names())

    # --- assert ------------------------------------------
    assert flop_count_field_names_1 == flop_type_names
    assert flop_count_field_names_2 == flop_type_names


def test_flop_counts_construction():
    # --- act ---------------------------------------------
    fc_0 = FlopCounts()
    fc_1 = FlopCounts(ADD=5, SQRT=6)
    fc_2 = FlopCounts(**{field_name: i + 1 for i, field_name in enumerate(FlopCounts.field_names())})

    expected_values = {
        "ABS": [0, 0, 1],
        "MINUS": [0, 0, 2],
        "EQUALS": [0, 0, 3],
        "GTE": [0, 0, 4],
        "LTE": [0, 0, 5],
        "CMP_ZERO": [0, 0, 6],
        "RND": [0, 0, 7],
        "ADD": [0, 5, 8],
        "SUB": [0, 0, 9],
        "MUL": [0, 0, 10],
        "DIV": [0, 0, 11],
        "SQRT": [0, 6, 12],
        "POW2": [0, 0, 13],
        "LOG2": [0, 0, 14],
        "POW": [0, 0, 15],
    }

    # --- assert ------------------------------------------
    for k, values_lst in expected_values.items():
        for i, (fc, value) in enumerate(zip([fc_0, fc_1, fc_2], values_lst)):
            assert getattr(fc, k) == value, f"fc_{i}.{k} should be {value} but is {getattr(fc, k)}"


def test_flop_counts_add():
    # --- arrange -----------------------------------------
    fc_0 = FlopCounts()
    fc_1 = FlopCounts()
    for i, field in enumerate(FlopCounts.field_names()):
        setattr(fc_0, field, i)
        setattr(fc_1, field, 2 * i + 2)

    # --- act ---------------------------------------------
    fc_sum_1 = fc_0 + fc_1
    fc_sum_2 = fc_1 + fc_0

    # --- assert ------------------------------------------
    for i, field in enumerate(FlopCounts.field_names()):
        assert getattr(fc_sum_1, field) == 3 * i + 2
        assert getattr(fc_sum_2, field) == 3 * i + 2


def test_flop_counts_sub():
    # --- arrange -----------------------------------------
    fc_0 = FlopCounts()
    fc_1 = FlopCounts()
    for i, field in enumerate(FlopCounts.field_names()):
        setattr(fc_0, field, i)
        setattr(fc_1, field, 2 * i + 2)

    # --- act ---------------------------------------------
    fc_diff_1 = fc_0 - fc_1
    fc_diff_2 = fc_1 - fc_0

    # --- assert ------------------------------------------
    for i, field in enumerate(FlopCounts.field_names()):
        assert getattr(fc_diff_1, field) == -i - 2
        assert getattr(fc_diff_2, field) == i + 2


def test_flop_counts_as_dict():
    # --- arrange -----------------------------------------
    orig_data = {flop_type: random.randint(0, 100) for flop_type in FlopType}
    flop_counts = FlopCounts(**{ft.name: n for ft, n in orig_data.items()})

    # --- act ---------------------------------------------
    counts_as_dict = flop_counts.as_dict()

    # --- assert ------------------------------------------
    assert counts_as_dict == orig_data


def test_flop_counts_total_count():
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts()
    expected_total_count = 0
    for flop_type in FlopType:
        count = random.randint(0, 100)
        setattr(flop_counts, flop_type.name, count)
        expected_total_count += count

    # --- act ---------------------------------------------
    total_count = flop_counts.total_count()

    # --- assert ------------------------------------------
    assert expected_total_count == total_count


def test_flop_counts_copy():
    # --- arrange -----------------------------------------
    fc_orig = FlopCounts(**{attr: random.randint(0, 10_000) for attr in FlopCounts.field_names()})

    # --- act ---------------------------------------------
    fc_copy = fc_orig.copy()

    # --- assert ------------------------------------------
    assert not fc_copy is fc_orig, "Copy should not be the same object as the original."
    for attr in FlopCounts.field_names():
        assert getattr(fc_orig, attr) == getattr(fc_copy, attr), f"Attribute {attr} does not match in copy."


def test_flop_counts_reset():
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts(**{attr: random.randint(0, 10_000) for attr in FlopCounts.field_names()})

    # --- act ---------------------------------------------
    flop_counts.reset()

    # --- assert ------------------------------------------
    for attr in FlopCounts.field_names():
        assert getattr(flop_counts, attr) == 0, f"Attribute {attr} not correctly set to 0 by reset()."


def test_flop_counts_total_weighted_cost_default():
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts(**{attr: random.randint(0, 10_000) for attr in FlopCounts.field_names()})
    default_weights = get_flop_weights()

    expected_total_cost = sum(
        getattr(flop_counts, flop_type.name) * default_weights.weights[flop_type] for flop_type in FlopType
    )

    # --- act ---------------------------------------------
    total_weighted_cost = flop_counts.total_weighted_cost()

    # --- assert ------------------------------------------
    assert total_weighted_cost == expected_total_cost


def test_flop_counts_total_weighted_cost_custom():
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts(**{attr: random.randint(0, 10_000) for attr in FlopCounts.field_names()})
    custom_weights = FlopWeights(weights={flop_type: i for i, flop_type in enumerate(FlopType, start=1)})

    expected_total_cost = sum(
        getattr(flop_counts, flop_type.name) * custom_weights.weights[flop_type] for flop_type in FlopType
    )

    # --- act ---------------------------------------------
    total_weighted_cost = flop_counts.total_weighted_cost(weights=custom_weights)

    # --- assert ------------------------------------------
    assert total_weighted_cost == expected_total_cost
