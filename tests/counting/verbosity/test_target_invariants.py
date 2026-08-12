"""The alias invariants that hold across every (verbosity level, paused) combination.

Increments go through one alias with more than one possible target, so the properties below are
easy to break from a distance -- notably by testing "is counting paused?" against the active
counts, which is wrong for a thread whose increments are routed through a logging target. They
are stated once here, as a matrix, rather than left to the module docstring.
"""

import pytest

from counted_float import FlopCounts, Verbosity
from counted_float._core.counting.thread_counter import _TLS


# ==================================================================================================
#  Which target increments go to, per (level, paused)
# ==================================================================================================
@pytest.mark.parametrize(
    ("level", "paused", "counted", "logged"),
    [
        (Verbosity.OFF, False, True, False),
        (Verbosity.OFF, True, False, False),
        (Verbosity.WARNING, False, True, False),
        (Verbosity.WARNING, True, False, False),
        (Verbosity.INFO, False, True, True),
        (Verbosity.INFO, True, False, False),
    ],
)
def test_increment_target(thread_counter, logged_lines, incr_flop, level, paused, counted, logged):
    # --- arrange -----------------------------------------
    thread_counter.set_verbosity(level)
    if paused:
        thread_counter.pause()

    # --- act ---------------------------------------------
    incr_flop("ADD")

    # --- assert ------------------------------------------
    # the alias points at the sink exactly while paused
    assert (_TLS.flop_counts is _TLS.flop_counts_inactive) is paused
    assert thread_counter.is_active() is (not paused)

    # counts are read back from the real counts, never through the alias
    assert thread_counter.flop_counts() == (FlopCounts(ADD=1) if counted else FlopCounts())

    assert len(logged_lines()) == (1 if logged else 0)


# ==================================================================================================
#  Changing the level while paused
# ==================================================================================================
def test_setting_verbosity_while_paused_does_not_resume(thread_counter, logged_lines, incr_flop):
    # --- arrange -----------------------------------------
    thread_counter.pause()

    # --- act ---------------------------------------------
    thread_counter.set_verbosity(Verbosity.INFO)
    incr_flop("ADD")

    # --- assert ------------------------------------------
    # the level lands, but the alias stays on the sink: switching it here would resume a thread
    # that asked to be paused
    assert _TLS.flop_counts is _TLS.flop_counts_inactive
    assert not thread_counter.is_active()
    assert thread_counter.flop_counts() == FlopCounts()
    assert logged_lines() == []


def test_resuming_picks_up_a_level_set_while_paused(thread_counter, logged_lines, incr_flop):
    # --- arrange -----------------------------------------
    thread_counter.pause()
    thread_counter.set_verbosity(Verbosity.INFO)

    # --- act ---------------------------------------------
    thread_counter.resume()
    incr_flop("ADD")

    # --- assert ------------------------------------------
    assert thread_counter.flop_counts() == FlopCounts(ADD=1)
    assert len(logged_lines()) == 1
