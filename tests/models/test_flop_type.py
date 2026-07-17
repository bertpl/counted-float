import pytest

from counted_float._core.models import FlopType


def test_flop_type_long_name():
    # --- act ---------------------------------------------
    all_long_names = {ft.long_name() for ft in FlopType}

    # --- assert ------------------------------------------
    assert len(all_long_names) == len(FlopType), "long names should be unique"


def test_flop_type_value_is_the_stable_name():
    # the serialized JSON key is the member value; keeping it equal to the name is what makes it a
    # stable identifier, decoupled from the (freely-changeable) display label
    assert all(ft.value == ft.name for ft in FlopType)


def test_flop_type_labels_are_unique_and_present():
    # --- act ---------------------------------------------
    labels = [ft.label for ft in FlopType]

    # --- assert ------------------------------------------
    assert all(labels), "every flop type has a display label"
    assert len(set(labels)) == len(FlopType), "labels should be unique"


@pytest.mark.parametrize("flop_type", list(FlopType))
def test_from_serialized_key_resolves_the_stable_name(flop_type: FlopType):
    assert FlopType.from_serialized_key(flop_type.name) is flop_type


def test_from_serialized_key_raises_on_unknown_key():
    with pytest.raises(ValueError, match="unrecognized flop-type key"):
        FlopType.from_serialized_key("not-a-flop-type")


def test_from_serialized_key_rejects_display_labels():
    # pre-2.0.0 files keyed on display labels; those are deliberately no longer readable
    with pytest.raises(ValueError, match="unrecognized flop-type key"):
        FlopType.from_serialized_key(FlopType.ADD.label)
