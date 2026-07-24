import pytest

from counted_float._core.counting.verbosity._output import (
    _COUNT_WIDTH,
    _LEVEL_WIDTH,
    _OPERATION_WIDTH,
    VerbosityWriter,
    _location_spans,
)


# ==================================================================================================
#  Uncounted lines
# ==================================================================================================
def test_write_uncounted_renders_the_consequence(logged_lines):
    # --- act ---------------------------------------------
    VerbosityWriter.shared().write_uncounted("erf", "returns a plain float", "my_algo.py:42")

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert "returns a plain float" in line, "The consequence is what a WARN line exists to say."


def test_write_uncounted_leaves_the_count_column_blank(logged_lines):
    # --- act ---------------------------------------------
    VerbosityWriter.shared().write_uncounted("erf", "returns a plain float", "my_algo.py:42")

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    count_column_start = _LEVEL_WIDTH + len("  ") + _OPERATION_WIDTH + len("  ")
    count_column = line[count_column_start : count_column_start + _COUNT_WIDTH]
    assert count_column.strip() == "", "Nothing was counted, so the count column stays empty."


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


def test_shared_returns_the_process_wide_singleton():
    # --- act ---------------------------------------------
    first = VerbosityWriter.shared()
    second = VerbosityWriter.shared()

    # --- assert ------------------------------------------
    assert isinstance(first, VerbosityWriter)
    assert first is second  # created once, then reused
