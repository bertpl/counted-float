import threading

import pytest

from counted_float._core.counting._thread_counter import THREAD_COUNTER, ThreadLocalFlopCounter
from counted_float._core.models import FlopCounts


@pytest.fixture
def thread_counter() -> ThreadLocalFlopCounter:
    """Fixture giving access to the calling thread's flop counter, reset BEFORE & AFTER each test."""

    # prepare
    THREAD_COUNTER.reset()

    # yield
    yield THREAD_COUNTER

    # cleanup
    THREAD_COUNTER.reset()


# ==================================================================================================
#  Facade behavior
# ==================================================================================================
def test_thread_counter_fixture(thread_counter):
    # --- assert 1 ----------------------------------------

    # check correct type and instance
    assert isinstance(thread_counter, ThreadLocalFlopCounter)
    assert thread_counter is THREAD_COUNTER, "The thread_counter fixture should be the same object as THREAD_COUNTER."

    # check correctly initialized
    assert thread_counter.flop_counts() == FlopCounts(), "The thread_counter fixture should be initialized to zero."
    assert thread_counter.is_active(), "The thread_counter fixture should be active."

    # --- act ---------------------------------------------
    thread_counter.incr_div()

    # --- assert 2 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 1
    assert thread_counter.flop_counts().DIV == 1
    assert THREAD_COUNTER.flop_counts() == thread_counter.flop_counts()


def test_thread_counter_total_count(thread_counter):
    # --- arrange -----------------------------------------
    thread_counter.incr_add()
    thread_counter.incr_mul()

    # --- act ---------------------------------------------
    total_count = thread_counter.total_count()

    # --- assert ------------------------------------------
    assert total_count == thread_counter.flop_counts().total_count()


def test_thread_counter_count_attributes(thread_counter):
    # --- arrange -----------------------------------------
    thread_counter.incr_add()
    thread_counter.incr_mul()

    # --- act & assert ------------------------------------
    assert thread_counter.ADD == 1, "ADD count is incorrect"
    assert thread_counter.MUL == 1, "MUL count is incorrect"
    for attr in FlopCounts.field_names():
        _ = getattr(thread_counter, attr)  # check the rest if we can access all attributes


def test_thread_counter_unknown_attribute_raises(thread_counter):
    # --- act & assert ------------------------------------
    with pytest.raises(AttributeError):
        _ = thread_counter.NOT_A_FLOP_TYPE


def test_thread_counter_counts(thread_counter):
    # --- act ---------------------------------------------
    thread_counter.incr_add()
    thread_counter.incr_add()
    thread_counter.incr_mul()

    # --- assert ------------------------------------------
    assert thread_counter.flop_counts().total_count() == 3
    assert thread_counter.flop_counts().ADD == 2
    assert thread_counter.flop_counts().MUL == 1


def test_thread_counter_reset(thread_counter):
    # --- arrange -----------------------------------------
    thread_counter.incr_add()
    thread_counter.incr_mul()
    thread_counter.pause()

    # --- act ---------------------------------------------
    thread_counter.reset()

    # --- assert ------------------------------------------
    assert thread_counter.is_active(), "reset() should also resume counting."
    assert thread_counter.flop_counts() == FlopCounts(), "After reset, the thread counter should be zero."


def test_thread_counter_pause_resume(thread_counter):
    # --- act 1 -------------------------------------------
    thread_counter.incr_mul()
    thread_counter.pause()

    # --- assert 1 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 1
    assert thread_counter.flop_counts().MUL == 1
    assert not thread_counter.is_active()

    # --- act 2 -------------------------------------------
    thread_counter.incr_sqrt()
    thread_counter.resume()
    thread_counter.incr_div()

    # --- assert 2 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 2
    assert thread_counter.flop_counts().MUL == 1
    assert thread_counter.flop_counts().DIV == 1
    assert thread_counter.is_active()

    # --- act 3 -------------------------------------------
    thread_counter.resume()  # again
    thread_counter.incr_div()
    thread_counter.pause()
    thread_counter.incr_rnd()
    thread_counter.pause()
    thread_counter.incr_rnd()
    thread_counter.resume()
    thread_counter.resume()
    thread_counter.incr_exp2()

    # --- assert 3 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 4
    assert thread_counter.flop_counts().MUL == 1
    assert thread_counter.flop_counts().DIV == 2
    assert thread_counter.flop_counts().EXP2 == 1
    assert thread_counter.is_active()


def test_thread_counter_all_incr_methods(thread_counter):
    # --- arrange -----------------------------------------
    incr_methods = [name for name in dir(ThreadLocalFlopCounter) if name.startswith("incr_")]

    # --- act ---------------------------------------------
    for name in incr_methods:
        getattr(thread_counter, name)()

    # --- assert ------------------------------------------
    # each incr_* method increments exactly one field, and no two share a field
    counts = thread_counter.flop_counts()
    assert counts.total_count() == len(incr_methods)
    for name in incr_methods:
        field = name.removeprefix("incr_").upper()
        assert getattr(counts, field) == 1, f"{name} should increment {field} by exactly 1"


# ==================================================================================================
#  Pause-swap invariant
# ==================================================================================================
def test_pause_swap_keeps_live_untouched(thread_counter):
    # --- arrange -----------------------------------------
    thread_counter.incr_add()
    snapshot = thread_counter.flop_counts()

    # --- act ---------------------------------------------
    thread_counter.pause()
    for _ in range(5):
        thread_counter.incr_mul()  # lands in the discard sink

    # --- assert ------------------------------------------
    # live counts unchanged during pause; the discard sink never leaks into flop_counts()
    assert thread_counter.flop_counts() == snapshot
    assert not thread_counter.is_active()

    thread_counter.resume()
    assert thread_counter.flop_counts() == snapshot
    assert thread_counter.is_active()


# ==================================================================================================
#  Per-thread semantics
# ==================================================================================================
def test_lazy_init_on_fresh_thread(thread_counter):
    # --- arrange -----------------------------------------
    result: dict[str, FlopCounts | bool] = {}

    def worker() -> None:
        # very first counter access on this thread: nothing pre-touched
        THREAD_COUNTER.incr_add()
        result["counts"] = THREAD_COUNTER.flop_counts()
        result["active"] = THREAD_COUNTER.is_active()

    # --- act ---------------------------------------------
    t = threading.Thread(target=worker)
    t.start()
    t.join()

    # --- assert ------------------------------------------
    assert result["counts"].ADD == 1, "the first counted op on a fresh thread must itself be counted"
    assert result["counts"].total_count() == 1
    assert result["active"] is True, "threads start unpaused"


def test_threads_have_isolated_counts(thread_counter):
    # --- arrange -----------------------------------------
    thread_counter.incr_add()  # main thread: 1 ADD
    observed: dict[str, FlopCounts] = {}

    def worker() -> None:
        for _ in range(3):
            THREAD_COUNTER.incr_mul()
        observed["worker"] = THREAD_COUNTER.flop_counts()

    # --- act ---------------------------------------------
    t = threading.Thread(target=worker)
    t.start()
    t.join()

    # --- assert ------------------------------------------
    assert observed["worker"] == FlopCounts(MUL=3), "worker thread must see only its own counts"
    assert thread_counter.flop_counts() == FlopCounts(ADD=1), "main thread must not see the worker's counts"


def test_pause_is_per_thread(thread_counter):
    # --- arrange -----------------------------------------
    thread_counter.pause()  # pause the main thread only
    observed: dict[str, FlopCounts] = {}

    def worker() -> None:
        THREAD_COUNTER.incr_mul()
        observed["worker"] = THREAD_COUNTER.flop_counts()

    # --- act ---------------------------------------------
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    thread_counter.incr_add()  # main thread is paused: not counted

    # --- assert ------------------------------------------
    assert observed["worker"] == FlopCounts(MUL=1), "a paused main thread must not pause other threads"
    assert thread_counter.flop_counts() == FlopCounts()
