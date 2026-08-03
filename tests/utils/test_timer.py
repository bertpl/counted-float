"""Timer's own logic: two clock readings, their difference, and the conversion to seconds.

Most of these drive a scripted clock rather than sleeping. Timer reads the wall clock through
time.perf_counter_ns(), so feeding it known readings pins its arithmetic exactly -- and keeps the
suite from asserting on how promptly the OS reschedules a sleeping thread, which no library
controls and which a saturated CI runner readily breaks. One test at the bottom does exercise the
real clock, so that faking cannot hide a Timer that never reads one.
"""

import time

import pytest

from counted_float._core.utils import Timer

_START_NS = 1_000_000


@pytest.fixture
def scripted_clock(monkeypatch) -> list[int]:
    """Make perf_counter_ns() return each value appended to the returned list, in order."""
    readings: list[int] = []
    values = iter(readings)
    monkeypatch.setattr(time, "perf_counter_ns", lambda: next(values))
    return readings


# =================================================================================================
#  Elapsed time
# =================================================================================================
@pytest.mark.parametrize(
    ("elapsed_ns", "expected_sec"),
    [
        (250_000_000, 0.25),
        (1_000_000_000, 1.0),
        (1, 1e-9),
        (0, 0.0),
    ],
)
def test_elapsed_is_the_difference_between_the_readings(scripted_clock, elapsed_ns: int, expected_sec: float):
    # --- arrange -----------------------------------------
    scripted_clock += [_START_NS, _START_NS + elapsed_ns]
    timer = Timer()

    # --- act ---------------------------------------------
    with timer:
        pass

    # --- assert ------------------------------------------
    assert timer.t_elapsed_nsec() == elapsed_ns
    assert timer.t_elapsed_sec() == expected_sec  # exact: seconds are nanoseconds / 1e9


def test_elapsed_is_frozen_once_the_block_exits(scripted_clock):
    # --- arrange -----------------------------------------
    scripted_clock += [_START_NS, _START_NS + 500_000_000, _START_NS + 9_000_000_000]
    timer = Timer()

    # --- act ---------------------------------------------
    with timer:
        pass
    later_reading = timer.t_elapsed_nsec()  # clock has moved on by 9s; the timer must not follow

    # --- assert ------------------------------------------
    assert later_reading == 500_000_000


def test_a_running_timer_tracks_the_clock(scripted_clock):
    # --- arrange -----------------------------------------
    scripted_clock += [_START_NS, _START_NS + 200_000_000, _START_NS + 700_000_000, _START_NS + 700_000_000]
    timer = Timer()

    # --- act ---------------------------------------------
    with timer:
        while_running = [timer.t_elapsed_nsec(), timer.t_elapsed_nsec()]

    # --- assert ------------------------------------------
    assert while_running == [200_000_000, 700_000_000]


def test_reading_a_timer_that_never_started_raises():
    # --- arrange -----------------------------------------
    timer = Timer()

    # --- act / assert ------------------------------------
    with pytest.raises(RuntimeError, match=r"^Timer has not been started\.$"):
        timer.t_elapsed_nsec()

    with pytest.raises(RuntimeError, match=r"^Timer has not been started\.$"):
        timer.t_elapsed_sec()


# =================================================================================================
#  Against the real clock
# =================================================================================================
def test_timer_measures_the_real_clock():
    """Insurance against the scripted clock hiding a Timer that reads no clock at all.

    Asserts only a floor: sleep() guarantees a minimum, never a maximum, and how long the OS takes
    to reschedule the woken thread is not something Timer promises anything about.
    """
    # --- arrange -----------------------------------------
    timer = Timer()

    # --- act ---------------------------------------------
    with timer:
        time.sleep(0.01)

    # --- assert ------------------------------------------
    assert timer.t_elapsed_sec() >= 0.01
    assert timer.t_elapsed_nsec() >= 10_000_000
    assert timer.t_elapsed_nsec() == pytest.approx(timer.t_elapsed_sec() * 1e9)
