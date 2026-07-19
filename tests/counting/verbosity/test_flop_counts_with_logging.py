import pytest

from counted_float import FlopCounts
from counted_float._core.counting.verbosity import FlopCountsWithLogging


@pytest.fixture
def counts() -> FlopCounts:
    return FlopCounts()


@pytest.fixture
def target(counts) -> FlopCountsWithLogging:
    return FlopCountsWithLogging(counts)


# ==================================================================================================
#  Forwarding to the real counts
# ==================================================================================================
def test_increments_reach_the_wrapped_counts(target, counts):
    # --- act ---------------------------------------------
    target.ADD += 1
    target.ADD += 1
    target.MUL += 3

    # --- assert ------------------------------------------
    assert counts == FlopCounts(ADD=2, MUL=3)


def test_reads_pass_through_to_the_wrapped_counts(target, counts):
    # --- arrange -----------------------------------------
    counts.DIV = 7

    # --- act & assert ------------------------------------
    assert target.DIV == 7


def test_every_count_field_is_proxied(target, counts):
    # --- act ---------------------------------------------
    for field_name in FlopCounts.field_names():
        setattr(target, field_name, 1)

    # --- assert ------------------------------------------
    assert counts == FlopCounts(**dict.fromkeys(FlopCounts.field_names(), 1))


# ==================================================================================================
#  Logging
# ==================================================================================================
def test_one_line_per_increment_statement(target, logged_lines):
    # --- act ---------------------------------------------
    target.ADD += 1
    target.MUL += 1

    # --- assert ------------------------------------------
    lines = logged_lines()
    assert len(lines) == 2
    assert "ADD" in lines[0]
    assert "MUL" in lines[1]


def test_a_bulk_increment_logs_one_line_carrying_its_size(target, logged_lines):
    # --- act ---------------------------------------------
    target.SUB += 4

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert "SUB" in line
    assert "+4" in line


def test_the_logged_line_reports_the_incrementing_location(target, logged_lines):
    # --- act ---------------------------------------------
    target.ADD += 1

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert "test_flop_counts_with_logging.py:" in line


# ==================================================================================================
#  Rationales
# ==================================================================================================
def test_a_note_is_rendered_on_the_next_line(target, logged_lines):
    # --- act ---------------------------------------------
    target.note("const exponent -> sqrt")
    target.SQRT += 1

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert "const exponent -> sqrt" in line


def test_a_note_is_consumed_by_a_single_line(target, logged_lines):
    # --- act ---------------------------------------------
    target.note("const exponent -> sqrt")
    target.SQRT += 1
    target.DIV += 1

    # --- assert ------------------------------------------
    explained, unexplained = logged_lines()
    assert "const exponent -> sqrt" in explained
    assert "const exponent -> sqrt" not in unexplained


def test_lines_without_a_note_carry_no_rationale(target, logged_lines):
    # --- act ---------------------------------------------
    target.ADD += 1

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    level, flop_type, count, location = line.split()
    assert (level, flop_type, count) == ("INFO", "ADD", "+1")
    assert location.startswith("test_flop_counts_with_logging.py:")
