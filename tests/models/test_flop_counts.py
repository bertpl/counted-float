import dataclasses
import math
import random

from counted_float import FlopWeights
from counted_float._core.counting.config import get_active_flop_weights
from counted_float._core.models import FlopCounts, FlopType


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
    fc_1 = FlopCounts(ADD=5, SQRT=6, TAN=3)
    fc_2 = FlopCounts(**{field_name: i + 1 for i, field_name in enumerate(FlopCounts.field_names())})

    expected_values = {
        "ABS": [0, 0, 1],
        "MINUS": [0, 0, 2],
        "COPYSIGN": [0, 0, 3],
        "COMP": [0, 0, 4],
        "RND": [0, 0, 5],
        "F2I": [0, 0, 6],
        "I2F": [0, 0, 7],
        "ADD": [0, 5, 8],
        "SUB": [0, 0, 9],
        "MUL": [0, 0, 10],
        "DIV": [0, 0, 11],
        "FMA": [0, 0, 12],
        "SQRT": [0, 6, 13],
        "CBRT": [0, 0, 14],
        "EXP": [0, 0, 15],
        "EXP2": [0, 0, 16],
        "EXP10": [0, 0, 17],
        "LOG": [0, 0, 18],
        "LOG2": [0, 0, 19],
        "LOG10": [0, 0, 20],
        "POW": [0, 0, 21],
        "SIN": [0, 0, 22],
        "COS": [0, 0, 23],
        "TAN": [0, 3, 24],
    }

    # --- assert ------------------------------------------
    for k, values_lst in expected_values.items():
        for i, (fc, value) in enumerate(zip([fc_0, fc_1, fc_2], values_lst, strict=False)):
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


def test_flop_counts_as_dict_nonzero_only():
    """nonzero_only drops exactly the zero-count entries and keeps FlopType order."""
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts(MUL=3, ADD=2)

    # --- act / assert ------------------------------------
    nonzero = flop_counts.as_dict(nonzero_only=True)
    assert nonzero == {FlopType.ADD: 2, FlopType.MUL: 3}
    assert list(nonzero) == [FlopType.ADD, FlopType.MUL]
    assert FlopCounts().as_dict(nonzero_only=True) == {}


def test_flop_counts_str_lists_only_nonzero_counts():
    """str() renders the constructor call rebuilding the counts; repr keeps every field."""
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts(MUL=3, ADD=2)

    # --- act / assert ------------------------------------
    assert str(flop_counts) == "FlopCounts(ADD=2, MUL=3)"
    assert str(FlopCounts()) == "FlopCounts()"
    assert "COPYSIGN=0" in repr(flop_counts)


def test_flop_counts_show_prints_nonzero_rows_and_total(capsys):
    """show() prints one row per nonzero count plus a total row, wrapped in braces."""
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts(MUL=3, ADD=2)

    # --- act ---------------------------------------------
    flop_counts.show()
    lines = capsys.readouterr().out.splitlines()

    # --- assert ------------------------------------------
    assert lines[0] == "{"
    assert lines[-1] == "}"
    assert len(lines) == 5  # braces + ADD + MUL + total
    assert "ADD" in lines[1]
    assert lines[1].rstrip().endswith("2")
    assert "MUL" in lines[2]
    assert lines[2].rstrip().endswith("3")
    assert "total" in lines[3]
    assert lines[3].rstrip().endswith("5")


def test_flop_counts_show_with_weights_appends_cost_column(capsys):
    """show(weights=...) appends count-times-weight per row and a weighted total."""
    # --- arrange -----------------------------------------
    flop_counts = FlopCounts(MUL=3, ADD=2)
    weights = FlopWeights(weights=dict.fromkeys(FlopType, 2.0))

    # --- act ---------------------------------------------
    flop_counts.show(weights=weights)
    lines = capsys.readouterr().out.splitlines()

    # --- assert ------------------------------------------
    assert "x" in lines[1]
    assert lines[1].rstrip().endswith("4.000")  # 2 x 2.0
    assert lines[2].rstrip().endswith("6.000")  # 3 x 2.0
    assert "total" in lines[3]
    assert lines[3].rstrip().endswith("10.000")


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
    assert fc_copy is not fc_orig, "Copy should not be the same object as the original."
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
    # types without a built-in weight yet (NaN, e.g. newly added and not re-measured) stay at
    # zero here; the NaN-propagation contract has its own test below
    default_weights = get_active_flop_weights()
    flop_counts = FlopCounts(
        **{
            flop_type.name: (0 if math.isnan(default_weights.weights[flop_type]) else random.randint(0, 10_000))
            for flop_type in FlopType
        }
    )

    expected_total_cost = sum(
        getattr(flop_counts, flop_type.name) * default_weights.weights[flop_type]
        for flop_type in FlopType
        if getattr(flop_counts, flop_type.name)
    )

    # --- act ---------------------------------------------
    total_weighted_cost = flop_counts.total_weighted_cost()

    # --- assert ------------------------------------------
    assert total_weighted_cost == expected_total_cost


def test_total_weighted_cost_missing_weight_only_affects_totals_that_used_it():
    """A NaN (missing) weight must not poison totals whose counts never touched that flop type."""
    # --- arrange -----------------------------------------
    weights = FlopWeights(weights={ft: (math.nan if ft is FlopType.COPYSIGN else 1.0) for ft in FlopType})

    # --- act / assert ------------------------------------
    assert FlopCounts(ADD=3).total_weighted_cost(weights=weights) == 3.0
    assert math.isnan(FlopCounts(ADD=3, COPYSIGN=1).total_weighted_cost(weights=weights))


def test_default_weights_with_unpriced_arity_types_still_yield_a_finite_total():
    """The arity types are NaN-weighted in the default consensus; a zero count of them must stay inert."""
    # --- arrange -----------------------------------------
    counts = FlopCounts(ADD=10, MUL=5, HYPOT=2)  # no HYPOT_XARG / DIST / DIST_XARG counted

    # --- act ---------------------------------------------
    total = counts.total_weighted_cost()  # uses the default consensus, where the arity types are NaN

    # --- assert ------------------------------------------
    assert math.isfinite(total), "an unpriced but uncounted flop type leaked NaN into the total"


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
