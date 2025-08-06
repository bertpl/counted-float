from counted_float._core.counting.models import FlopType


def test_flop_type_long_name():
    # --- act ---------------------------------------------
    all_long_names = {ft.long_name() for ft in FlopType}

    # --- assert ------------------------------------------
    assert len(all_long_names) == len(FlopType), "long names should be unique"
