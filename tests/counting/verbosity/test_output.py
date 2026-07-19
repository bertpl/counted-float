import pytest

from counted_float._core.counting.verbosity._output import _location_spans


# ==================================================================================================
#  Location rendering
# ==================================================================================================
def test_a_location_renders_its_line_number_at_full_intensity():
    # --- act ---------------------------------------------
    spans = _location_spans("my_algo.py:42")

    # --- assert ------------------------------------------
    assert spans == (("my_algo.py:", "dim"), ("42", "default"))


@pytest.mark.parametrize("location", ["<unknown>", ""])
def test_a_location_without_a_line_number_renders_as_one_span(location):
    # --- act ---------------------------------------------
    spans = _location_spans(location)

    # --- assert ------------------------------------------
    assert spans == ((location, "dim"),)
