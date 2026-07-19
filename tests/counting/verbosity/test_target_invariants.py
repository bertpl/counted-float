"""The alias invariants that hold across every (verbosity level, paused) combination.

Increments go through one alias with more than one possible target, so the properties below are
easy to break from a distance -- notably by testing "is counting paused?" against the active
counts, which is wrong for a thread whose increments are routed through a logging target. They
are stated once here, as a matrix, rather than left to the module docstring.
"""

import pytest

from counted_float import FlopCounts, Verbosity
from counted_float._core.counting._thread_counter import _TLS


@pytest.mark.parametrize(
    ("level", "paused", "counted", "logged"),
    [
        (Verbosity.OFF, False, True, False),
        (Verbosity.OFF, True, False, False),
        (Verbosity.INFO, False, True, True),
        (Verbosity.INFO, True, False, False),
    ],
)
def test_increment_target(thread_counter, logged_lines, level, paused, counted, logged):
    # --- arrange -----------------------------------------
    thread_counter.set_verbosity(level)
    if paused:
        thread_counter.pause()

    # --- act ---------------------------------------------
    thread_counter.incr_add()

    # --- assert ------------------------------------------
    # the alias points at the sink exactly while paused
    assert (_TLS.flop_counts is _TLS.flop_counts_inactive) is paused
    assert thread_counter.is_active() is (not paused)

    # counts are read back from the real counts, never through the alias
    assert thread_counter.flop_counts() == (FlopCounts(ADD=1) if counted else FlopCounts())

    assert len(logged_lines()) == (1 if logged else 0)
