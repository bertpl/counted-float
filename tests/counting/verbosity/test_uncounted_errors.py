"""Verbosity.ERROR raises at every operation that WARNING would report as a line."""

import math
import pickle

import pytest

from counted_float import (
    CountedFloat,
    FlopCountingContext,
    FlopCounts,
    PauseFlopCounting,
    UncountedOperationError,
    Verbosity,
)

from .conftest import EXTRA_ARGUMENTS, UNCOUNTED_FUNCTION_NAMES


# ==================================================================================================
#  What raises
# ==================================================================================================
@pytest.mark.parametrize("function_name", UNCOUNTED_FUNCTION_NAMES)
def test_every_uncounted_math_function_raises(function_name):
    """Each uncounted math function raises, naming itself as the operation."""
    # --- arrange ----------------------
    arguments = (CountedFloat(2.5), *EXTRA_ARGUMENTS.get(function_name, ()))

    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.ERROR), pytest.raises(UncountedOperationError) as error:
        # resolved inside the context, where the replacements are installed
        getattr(math, function_name)(*arguments)

    # --- assert -----------------------
    assert error.value.operation == function_name


def test_as_integer_ratio_raises():
    """`as_integer_ratio` raises, named as the float method it is."""
    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.ERROR), pytest.raises(UncountedOperationError) as error:
        CountedFloat(1.5).as_integer_ratio()

    # --- assert -----------------------
    assert error.value.operation == "float.as_integer_ratio"


def test_the_error_locates_the_calling_line():
    """The error's location is the user's line, not a frame inside the library."""
    # --- arrange ----------------------
    x = CountedFloat(2.5)

    def call_ulp() -> float:
        return math.ulp(x)  # the calling line: the one below the def

    calling_line = call_ulp.__code__.co_firstlineno + 1

    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.ERROR), pytest.raises(UncountedOperationError) as error:
        call_ulp()

    # --- assert -----------------------
    assert error.value.location == f"test_uncounted_errors.py:{calling_line}"


def test_plain_arguments_raise_nothing():
    """A call without counted values loses no count, so it raises nothing."""
    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.ERROR):
        result = math.ulp(2.5)

    # --- assert -----------------------
    assert result == 2.0**-51


def test_a_paused_call_raises_nothing():
    """Paused operations are deliberately uncounted, so they raise nothing."""
    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.ERROR), PauseFlopCounting():
        result = math.ulp(CountedFloat(2.5))

    # --- assert -----------------------
    assert result == 2.0**-51


# ==================================================================================================
#  How it raises
# ==================================================================================================
def test_every_call_raises():
    """A call site raises on every call, where WARNING reports it once."""
    # --- arrange ----------------------
    x = CountedFloat(2.5)

    # --- act & assert -----------------
    with FlopCountingContext(verbosity=Verbosity.ERROR):
        for _ in range(3):
            with pytest.raises(UncountedOperationError):
                math.ulp(x)


def test_a_call_site_reported_at_warning_still_raises(logged_lines):
    """WARNING's record of reported call sites does not stop ERROR from raising."""
    # --- arrange ----------------------
    x = CountedFloat(2.5)

    def call_ulp() -> float:
        return math.ulp(x)  # one call site, reached at both levels

    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        call_ulp()
    with FlopCountingContext(verbosity=Verbosity.ERROR), pytest.raises(UncountedOperationError):
        call_ulp()

    # --- assert -----------------------
    (line,) = logged_lines()
    assert line.split()[:2] == ["WARN", "ulp"]


def test_the_replaced_function_does_not_run(make_probe_wrapper):
    """The error is raised before the replaced function runs."""
    # --- arrange ----------------------
    delegate_calls: list = []
    wrapper = make_probe_wrapper("probe_error", delegate_calls)

    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.ERROR), pytest.raises(UncountedOperationError):
        wrapper(CountedFloat(2.5))

    # --- assert -----------------------
    assert delegate_calls == []


def test_error_prints_nothing_and_counts_as_usual(logged_lines):
    """ERROR writes no line, and counts the countable operations as every level does."""
    # --- arrange ----------------------
    x = CountedFloat(2.5)

    # --- act --------------------------
    with FlopCountingContext(verbosity=Verbosity.ERROR) as ctx:
        _ = x * x
        with pytest.raises(UncountedOperationError):
            math.ulp(x)

    # --- assert -----------------------
    assert ctx.flop_counts() == FlopCounts(MUL=1)
    assert logged_lines() == []


@pytest.mark.parametrize("inner_level", [level for level in Verbosity if level is not Verbosity.ERROR])
def test_an_inner_context_at_another_level_suspends_error(inner_level):
    """The innermost context's level wins, as for every level, and ERROR resumes once it exits."""
    # --- arrange ----------------------
    x = CountedFloat(2.5)

    # --- act & assert -----------------
    with FlopCountingContext(verbosity=Verbosity.ERROR):
        with FlopCountingContext(verbosity=inner_level):
            _ = math.ulp(x)
        with pytest.raises(UncountedOperationError):
            math.ulp(x)


# ==================================================================================================
#  The error itself
# ==================================================================================================
def test_the_message_names_the_operation_location_and_consequence():
    """The message reads as one sentence about the call that could not be counted."""
    # --- act --------------------------
    error = UncountedOperationError("frexp", "uncounted; result is a plain float", "algo.py:7")

    # --- assert -----------------------
    assert str(error) == "frexp at algo.py:7 could not be counted: uncounted; result is a plain float"


def test_the_error_survives_pickling():
    """Unpickling restores every field and the message, as multiprocessing needs."""
    # --- arrange ----------------------
    error = UncountedOperationError("frexp", "uncounted; result is a plain float", "algo.py:7")

    # --- act --------------------------
    restored = pickle.loads(pickle.dumps(error))  # noqa: S301 -- the payload was pickled one line up

    # --- assert -----------------------
    assert (restored.operation, restored.consequence, restored.location) == (
        "frexp",
        "uncounted; result is a plain float",
        "algo.py:7",
    )
    assert str(restored) == str(error)
