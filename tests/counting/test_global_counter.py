from counted_float._core.counting._global_counter import GLOBAL_COUNTER, GlobalFlopCounter
from counted_float._core.counting.models import FlopCounts


def test_global_counter_fixture(global_counter):
    # --- assert 1 ----------------------------------------

    # check correct type and instance
    assert isinstance(global_counter, GlobalFlopCounter)
    assert global_counter is GLOBAL_COUNTER, "The global_counter fixture should be the same object as GLOBAL_COUNTER."

    # check correctly initialized
    assert global_counter.flop_counts() == FlopCounts(), "The global_counter fixture should be initialized to zero."
    assert global_counter.is_active(), "The global_counter fixture should be active."

    # --- act ---------------------------------------------
    global_counter.incr_div()

    # --- assert 2 ----------------------------------------
    assert global_counter.flop_counts().total_count() == 1
    assert global_counter.flop_counts().DIV == 1
    assert GLOBAL_COUNTER.flop_counts() == global_counter.flop_counts()


def test_global_counter_total_count(global_counter):
    # --- arrange -----------------------------------------
    global_counter.incr_add()
    global_counter.incr_mul()

    # --- act ---------------------------------------------
    total_count = global_counter.total_count()

    # --- assert ------------------------------------------
    assert total_count == global_counter.flop_counts().total_count()


def test_global_counter_count_attributes(global_counter):
    # --- arrange -----------------------------------------
    global_counter.incr_add()
    global_counter.incr_mul()

    # --- act & assert ------------------------------------
    assert global_counter.ADD == 1, "ADD count is incorrect"
    assert global_counter.MUL == 1, "MUL count is incorrect"
    for attr in FlopCounts.field_names():
        _ = getattr(global_counter, attr)  # check the rest if we can access all attributes


def test_global_counter_counts():
    # --- act ---------------------------------------------
    GLOBAL_COUNTER.incr_add()
    GLOBAL_COUNTER.incr_add()
    GLOBAL_COUNTER.incr_mul()

    # --- assert ------------------------------------------
    assert isinstance(GLOBAL_COUNTER, GlobalFlopCounter), "GLOBAL_COUNTER should be an instance of GlobalFlopCounter."
    assert GLOBAL_COUNTER.flop_counts().total_count() == 3
    assert GLOBAL_COUNTER.flop_counts().ADD == 2
    assert GLOBAL_COUNTER.flop_counts().MUL == 1


def test_global_counter_reset():
    # --- arrange -----------------------------------------
    GLOBAL_COUNTER.incr_add()
    GLOBAL_COUNTER.incr_mul()
    GLOBAL_COUNTER.pause()

    # --- act ---------------------------------------------
    GLOBAL_COUNTER.reset()

    # --- assert ------------------------------------------
    assert GLOBAL_COUNTER.is_active()
    assert GLOBAL_COUNTER.flop_counts() == FlopCounts(), "After reset, the global counter should be zero."


def test_global_counter_pause_resume(global_counter):
    # --- act 1 -------------------------------------------
    global_counter.incr_mul()
    global_counter.pause()

    # --- assert 1 ----------------------------------------
    assert global_counter.flop_counts().total_count() == 1
    assert global_counter.flop_counts().MUL == 1
    assert not global_counter.is_active()

    # --- act 2 -------------------------------------------
    global_counter.incr_sqrt()
    global_counter.resume()
    global_counter.incr_div()

    # --- assert 2 ----------------------------------------
    assert global_counter.flop_counts().total_count() == 2
    assert global_counter.flop_counts().MUL == 1
    assert global_counter.flop_counts().DIV == 1
    assert global_counter.is_active()

    # --- act 3 -------------------------------------------
    global_counter.resume()  # again
    global_counter.incr_div()
    global_counter.pause()
    global_counter.incr_rnd()
    global_counter.pause()
    global_counter.incr_rnd()
    global_counter.resume()
    global_counter.resume()
    global_counter.incr_pow2()

    # --- assert 3 ----------------------------------------
    assert global_counter.flop_counts().total_count() == 4
    assert global_counter.flop_counts().MUL == 1
    assert global_counter.flop_counts().DIV == 2
    assert global_counter.flop_counts().POW2 == 1
    assert global_counter.is_active()
