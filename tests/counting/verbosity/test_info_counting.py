import math

import pytest

from counted_float import CountedFloat, FlopCountingContext, PauseFlopCounting, Verbosity
from counted_float._core.counting._thread_counter import THREAD_COUNTER


# ==================================================================================================
#  What gets logged
# ==================================================================================================
def test_info_logs_every_counted_flop(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO):
        _ = (x * x) + x

    # --- assert ------------------------------------------
    lines = logged_lines()
    assert len(lines) == 2
    assert "MUL" in lines[0]
    assert "ADD" in lines[1]


def test_off_logs_nothing(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext():
        _ = (x * x) + x

    # --- assert ------------------------------------------
    assert logged_lines() == []


def test_logged_lines_locate_the_user_expression_not_the_library(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO):
        _ = math.sqrt(x)

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert "test_info_counting.py:" in line, "The counting machinery's own frames should be skipped."


@pytest.mark.parametrize(
    ("expression", "flop_type", "rationale"),
    [
        (lambda x: x**2, "MUL", "const exponent -> square-and-multiply"),
        (lambda x: x**0.5, "SQRT", "const exponent 0.5 -> sqrt"),
        (lambda x: x**-1, "DIV", "const exponent -1 -> reciprocal"),
        (lambda x: 2**x, "EXP2", "const base 2 -> exp2"),
        (lambda x: 10**x, "EXP10", "const base 10 -> exp10"),
        (lambda x: math.log(x, 2), "LOG2", "const base 2 -> log2"),
        (lambda x: math.log(x, 10), "LOG10", "const base 10 -> log10"),
        (lambda x: math.log(x, 7.0), "LOG", "const base -> log(x) * 1/log(base)"),
        (lambda x: math.log(x, CountedFloat(7.0)), "LOG", "runtime base -> log(x)/log(base)"),
    ],
)
def test_strength_reductions_are_explained(logged_lines, expression, flop_type, rationale):
    # --- arrange -----------------------------------------
    x = CountedFloat(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO):
        _ = expression(x)

    # --- assert ------------------------------------------
    first_line = logged_lines()[0]
    assert flop_type in first_line
    assert rationale in first_line


def test_plainly_counted_flops_carry_no_rationale(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO):
        _ = x * x

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    fields = line.split()
    assert fields[:3] == ["INFO", "MUL", "+1"]
    assert len(fields) == 4, "Without a rationale, a line holds only level, flop type, count and location."


# ==================================================================================================
#  Logging does not disturb counting
# ==================================================================================================
def test_counts_are_the_same_whether_or_not_they_are_logged():
    # --- arrange -----------------------------------------
    def counted_work() -> None:
        x = CountedFloat(3.0)
        _ = ((x * x) + x) / x
        _ = math.dist([x, x], [x, x])
        _ = x**2

    # --- act ---------------------------------------------
    with FlopCountingContext() as silent:
        counted_work()
    with FlopCountingContext(verbosity=Verbosity.INFO) as verbose:
        counted_work()

    # --- assert ------------------------------------------
    assert verbose.flop_counts() == silent.flop_counts()


# ==================================================================================================
#  Interaction with pausing
# ==================================================================================================
def test_paused_flops_are_neither_counted_nor_logged(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO) as ctx:
        with PauseFlopCounting():
            _ = x * x
        _ = x + x

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert "ADD" in line
    assert ctx.flop_counts().MUL == 0


# ==================================================================================================
#  Nesting and restoration
# ==================================================================================================
def test_the_innermost_context_decides_the_level(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(3.0)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO):
        _ = x * x
        with FlopCountingContext():
            _ = x / x
        _ = x + x

    # --- assert ------------------------------------------
    lines = logged_lines()
    assert [line.split()[1] for line in lines] == ["MUL", "ADD"], (
        "The nested silent context should have silenced only the flops inside it."
    )


def test_the_level_is_restored_when_the_context_exits():
    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO):
        level_inside = THREAD_COUNTER.verbosity()
    level_after = THREAD_COUNTER.verbosity()

    # --- assert ------------------------------------------
    assert level_inside == Verbosity.INFO
    assert level_after == Verbosity.OFF


def test_the_level_is_restored_when_the_block_raises():
    # --- act ---------------------------------------------
    with pytest.raises(ValueError, match="counted"), FlopCountingContext(verbosity=Verbosity.INFO):
        raise ValueError("counted work went wrong")

    # --- assert ------------------------------------------
    assert THREAD_COUNTER.verbosity() == Verbosity.OFF


def test_re_entering_one_context_keeps_its_level():
    # --- arrange -----------------------------------------
    ctx = FlopCountingContext(verbosity=Verbosity.INFO)

    # --- act ---------------------------------------------
    with ctx:
        with ctx:
            level_nested = THREAD_COUNTER.verbosity()
        level_outer = THREAD_COUNTER.verbosity()

    # --- assert ------------------------------------------
    assert level_nested == Verbosity.INFO
    assert level_outer == Verbosity.INFO
