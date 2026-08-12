import threading

import pytest

from counted_float import Verbosity
from counted_float._core.counting.thread_counter import THREAD_COUNTER, ThreadLocalFlopCounter
from counted_float._core.models import FlopCounts


# ==================================================================================================
#  Facade behavior
# ==================================================================================================
def test_thread_counter_fixture(thread_counter, incr_flop):
    # --- assert 1 ----------------------------------------

    # check correct type and instance
    assert isinstance(thread_counter, ThreadLocalFlopCounter)
    assert thread_counter is THREAD_COUNTER, "The thread_counter fixture should be the same object as THREAD_COUNTER."

    # check correctly initialized
    assert thread_counter.flop_counts() == FlopCounts(), "The thread_counter fixture should be initialized to zero."
    assert thread_counter.is_active(), "The thread_counter fixture should be active."

    # --- act ---------------------------------------------
    incr_flop("DIV")

    # --- assert 2 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 1
    assert thread_counter.flop_counts().DIV == 1
    assert THREAD_COUNTER.flop_counts() == thread_counter.flop_counts()


def test_thread_counter_total_count(thread_counter, incr_flop):
    # --- arrange -----------------------------------------
    incr_flop("ADD")
    incr_flop("MUL")

    # --- act ---------------------------------------------
    total_count = thread_counter.total_count()

    # --- assert ------------------------------------------
    assert total_count == thread_counter.flop_counts().total_count()


def test_thread_counter_count_attributes(thread_counter, incr_flop):
    # --- arrange -----------------------------------------
    incr_flop("ADD")
    incr_flop("MUL")

    # --- act & assert ------------------------------------
    assert thread_counter.ADD == 1, "ADD count is incorrect"
    assert thread_counter.MUL == 1, "MUL count is incorrect"
    for attr in FlopCounts.field_names():
        _ = getattr(thread_counter, attr)  # check the rest if we can access all attributes


def test_thread_counter_unknown_attribute_raises(thread_counter):
    # --- act & assert ------------------------------------
    with pytest.raises(AttributeError, match=r"^'ThreadLocalFlopCounter' object has no attribute 'NOT_A_FLOP_TYPE'$"):
        _ = thread_counter.NOT_A_FLOP_TYPE


def test_thread_counter_counts(thread_counter, incr_flop):
    # --- act ---------------------------------------------
    incr_flop("ADD")
    incr_flop("ADD")
    incr_flop("MUL")

    # --- assert ------------------------------------------
    assert thread_counter.flop_counts().total_count() == 3
    assert thread_counter.flop_counts().ADD == 2
    assert thread_counter.flop_counts().MUL == 1


def test_thread_counter_reset(thread_counter, incr_flop):
    # --- arrange -----------------------------------------
    incr_flop("ADD")
    incr_flop("MUL")
    thread_counter.pause()

    # --- act ---------------------------------------------
    thread_counter.reset()

    # --- assert ------------------------------------------
    assert thread_counter.is_active(), "reset() should also resume counting."
    assert thread_counter.flop_counts() == FlopCounts(), "After reset, the thread counter should be zero."


def test_thread_counter_pause_resume(thread_counter, incr_flop):
    # --- act 1 -------------------------------------------
    incr_flop("MUL")
    thread_counter.pause()

    # --- assert 1 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 1
    assert thread_counter.flop_counts().MUL == 1
    assert not thread_counter.is_active()

    # --- act 2 -------------------------------------------
    incr_flop("SQRT")
    thread_counter.resume()
    incr_flop("DIV")

    # --- assert 2 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 2
    assert thread_counter.flop_counts().MUL == 1
    assert thread_counter.flop_counts().DIV == 1
    assert thread_counter.is_active()

    # --- act 3 -------------------------------------------
    thread_counter.resume()  # again
    incr_flop("DIV")
    thread_counter.pause()
    incr_flop("RND")
    thread_counter.pause()
    incr_flop("RND")
    thread_counter.resume()
    thread_counter.resume()
    incr_flop("EXP2")

    # --- assert 3 ----------------------------------------
    assert thread_counter.flop_counts().total_count() == 4
    assert thread_counter.flop_counts().MUL == 1
    assert thread_counter.flop_counts().DIV == 2
    assert thread_counter.flop_counts().EXP2 == 1
    assert thread_counter.is_active()


def test_every_count_field_is_reachable(thread_counter, incr_flop):
    # --- act ---------------------------------------------
    for field in FlopCounts.field_names():
        incr_flop(field)

    # --- assert ------------------------------------------
    # each increment lands in its own field, and the read path reports every one of them
    counts = thread_counter.flop_counts()
    assert counts.total_count() == len(FlopCounts.field_names())
    for field in FlopCounts.field_names():
        assert getattr(counts, field) == 1, f"incrementing {field} should raise exactly that count to 1"


# ==================================================================================================
#  Pause-swap invariant
# ==================================================================================================
def test_pause_swap_keeps_live_untouched(thread_counter, incr_flop):
    # --- arrange -----------------------------------------
    incr_flop("ADD")
    snapshot = thread_counter.flop_counts()

    # --- act ---------------------------------------------
    thread_counter.pause()
    for _ in range(5):
        incr_flop("MUL")  # lands in the discard sink

    # --- assert ------------------------------------------
    # live counts unchanged during pause; the discard sink never leaks into flop_counts()
    assert thread_counter.flop_counts() == snapshot
    assert not thread_counter.is_active()

    thread_counter.resume()
    assert thread_counter.flop_counts() == snapshot
    assert thread_counter.is_active()


# ==================================================================================================
#  Verbosity
# ==================================================================================================
def test_verbosity_defaults_to_off(thread_counter):
    # --- act & assert ------------------------------------
    assert thread_counter.verbosity() == Verbosity.OFF


def test_set_verbosity_returns_the_replaced_level(thread_counter):
    # --- act ---------------------------------------------
    replaced_by_info = thread_counter.set_verbosity(Verbosity.INFO)
    replaced_by_off = thread_counter.set_verbosity(Verbosity.OFF)

    # --- assert ------------------------------------------
    assert replaced_by_info == Verbosity.OFF
    assert replaced_by_off == Verbosity.INFO


def test_counting_through_the_logging_target_still_counts(thread_counter, capsys, incr_flop):
    # --- act ---------------------------------------------
    thread_counter.set_verbosity(Verbosity.INFO)
    incr_flop("ADD")

    # --- assert ------------------------------------------
    assert thread_counter.is_active(), "A logging target is not a paused one."
    assert thread_counter.flop_counts() == FlopCounts(ADD=1)
    assert "ADD" in capsys.readouterr().err


def test_pause_and_resume_keep_the_logging_target(thread_counter, capsys, incr_flop):
    # --- arrange -----------------------------------------
    thread_counter.set_verbosity(Verbosity.INFO)

    # --- act ---------------------------------------------
    thread_counter.pause()
    incr_flop("MUL")  # lands in the discard sink, so there is nothing to log
    paused_output = capsys.readouterr().err
    thread_counter.resume()
    incr_flop("MUL")
    resumed_output = capsys.readouterr().err

    # --- assert ------------------------------------------
    assert paused_output == ""
    assert "MUL" in resumed_output
    assert thread_counter.flop_counts() == FlopCounts(MUL=1)


def test_reset_resumes_into_the_logging_target(thread_counter, capsys, incr_flop):
    # --- arrange -----------------------------------------
    thread_counter.set_verbosity(Verbosity.INFO)
    thread_counter.pause()

    # --- act ---------------------------------------------
    thread_counter.reset()  # reset also resumes
    incr_flop("ADD")

    # --- assert ------------------------------------------
    assert thread_counter.is_active()
    assert "ADD" in capsys.readouterr().err


# ==================================================================================================
#  Per-thread semantics
# ==================================================================================================
def test_lazy_init_on_fresh_thread(thread_counter, incr_flop):
    # --- arrange -----------------------------------------
    result: dict[str, FlopCounts | bool] = {}

    def worker() -> None:
        # very first counter access on this thread: nothing pre-touched
        incr_flop("ADD")
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


def test_threads_have_isolated_counts(thread_counter, incr_flop):
    # --- arrange -----------------------------------------
    incr_flop("ADD")  # main thread: 1 ADD
    observed: dict[str, FlopCounts] = {}

    def worker() -> None:
        for _ in range(3):
            incr_flop("MUL")
        observed["worker"] = THREAD_COUNTER.flop_counts()

    # --- act ---------------------------------------------
    t = threading.Thread(target=worker)
    t.start()
    t.join()

    # --- assert ------------------------------------------
    assert observed["worker"] == FlopCounts(MUL=3), "worker thread must see only its own counts"
    assert thread_counter.flop_counts() == FlopCounts(ADD=1), "main thread must not see the worker's counts"


def test_pause_is_per_thread(thread_counter, incr_flop):
    # --- arrange -----------------------------------------
    thread_counter.pause()  # pause the main thread only
    observed: dict[str, FlopCounts] = {}

    def worker() -> None:
        incr_flop("MUL")
        observed["worker"] = THREAD_COUNTER.flop_counts()

    # --- act ---------------------------------------------
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    incr_flop("ADD")  # main thread is paused: not counted

    # --- assert ------------------------------------------
    assert observed["worker"] == FlopCounts(MUL=1), "a paused main thread must not pause other threads"
    assert thread_counter.flop_counts() == FlopCounts()
