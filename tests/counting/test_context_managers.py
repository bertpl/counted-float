import math

import pytest

from counted_float._core.counting._context_managers import FlopCountingContext, PauseFlopCounting
from counted_float._core.counting._counted_float import CountedFloat
from counted_float._core.counting._thread_counter import THREAD_COUNTER


# =================================================================================================
#  FlopCountingContext
# =================================================================================================
def test_flop_counting_context_construction():
    FlopCountingContext()


def test_flop_counting_context_is_active():
    # --- arrange -----------------------------------------
    fcc = FlopCountingContext()

    # --- act ---------------------------------------------
    is_active_before = fcc.is_active()
    with fcc:
        is_active_while = fcc.is_active()
    is_active_after = fcc.is_active()

    # --- assert ------------------------------------------
    assert not is_active_before
    assert is_active_while
    assert not is_active_after


def test_flop_counting_context_counting_basic():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    _ = cf1 / cf2  # should not be counted
    with FlopCountingContext() as fcc:
        _ = cf1 + cf2  # should be counted
    _ = cf1 * cf2  # should not be counted

    flop_counts = fcc.flop_counts()

    # --- assert ------------------------------------------
    assert flop_counts.total_count() == 1
    assert flop_counts.ADD == 1


def test_flop_counting_context_counting_nested():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    _ = cf1 / cf2  # should not be counted
    with FlopCountingContext() as fcc1:
        _ = cf1 + cf2  # should be counted in fcc1
        with FlopCountingContext() as fcc2:
            _ = cf1 * cf2  # should be counted in fcc1 & fcc2
        _ = cf1**cf2  # should be counted in fcc1

    flop_counts_1 = fcc1.flop_counts()
    flop_counts_2 = fcc2.flop_counts()

    # --- assert ------------------------------------------

    # check fcc1 counts
    assert flop_counts_1.total_count() == 3
    assert flop_counts_1.ADD == 1
    assert flop_counts_1.MUL == 1
    assert flop_counts_1.POW == 1

    # check fcc2 counts
    assert flop_counts_2.total_count() == 1
    assert flop_counts_2.MUL == 1


def test_flop_counting_context_pause_resume_basic():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        # --- part 1 ---
        is_active_1 = fcc.is_active()
        _ = cf1 + cf2  # should be counted

        # --- part 2 ---
        fcc.pause()
        is_active_2 = fcc.is_active()
        _ = cf1 * cf2  # should not be counted

        # --- part 3 ---
        fcc.resume()
        is_active_3 = fcc.is_active()
        _ = cf1**cf2  # should be counted

        # --- part 4 ---
        fcc.pause()  # pause one last time, to check it works to exit like this
        is_active_4 = fcc.is_active()
        _ = cf1 - cf2  # should not be counted

    is_active_5 = fcc.is_active()

    flop_counts = fcc.flop_counts()

    # --- assert ------------------------------------------
    assert flop_counts.total_count() == 2
    assert flop_counts.ADD == 1
    assert flop_counts.POW == 1
    assert is_active_1
    assert not is_active_2
    assert is_active_3
    assert not is_active_4
    assert not is_active_5


def test_flop_counting_context_pause_resume_nested():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc1, FlopCountingContext() as fcc2:
        _ = cf1 + cf2  # should be counted in fcc1 & fcc2
        fcc2.pause()
        _ = cf1 * cf2  # should be counted in fcc1, not in fcc2
        fcc2.resume()
        _ = cf1**cf2  # should be counted in fcc1 & fcc2
        fcc1.pause()
        _ = cf1 - cf2  # should be counted in fcc2, not in fcc1
        fcc2.pause()
        _ = cf1 / cf2  # should not be counted in either fcc1 or fcc2

    flop_counts_1 = fcc1.flop_counts()
    flop_counts_2 = fcc2.flop_counts()

    # --- assert ------------------------------------------
    assert flop_counts_1.total_count() == 3
    assert flop_counts_1.ADD == 1
    assert flop_counts_1.MUL == 1
    assert flop_counts_1.POW == 1
    assert flop_counts_2.total_count() == 3
    assert flop_counts_2.ADD == 1
    assert flop_counts_2.POW == 1
    assert flop_counts_2.SUB == 1


def test_flop_counting_context_flop_counts_advanced():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        flop_counts_1 = fcc.flop_counts()
        _ = cf1 + cf2
        flop_counts_2 = fcc.flop_counts()
        _ = cf1 * cf2
        flop_counts_3 = fcc.flop_counts()
    flop_counts_4 = fcc.flop_counts()

    # --- assert ------------------------------------------
    assert flop_counts_1.total_count() == 0
    assert flop_counts_2.total_count() == 1
    assert flop_counts_3.total_count() == 2
    assert flop_counts_4.total_count() == 2


# =================================================================================================
#  PauseFlopCounting
# =================================================================================================
def test_pause_flop_counting():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc1, FlopCountingContext() as fcc2:
        _ = cf1 + cf2  # should be counted in fcc1 & fcc2
        with PauseFlopCounting():
            _ = cf1 / cf2  # should be counted anywhere
            with FlopCountingContext() as fcc3:
                _ = cf1 * cf2  # should be counted anywhere

    flop_counts_1 = fcc1.flop_counts()
    flop_counts_2 = fcc2.flop_counts()
    flop_counts_3 = fcc3.flop_counts()

    # --- assert ------------------------------------------
    assert flop_counts_1.total_count() == 1
    assert flop_counts_2.total_count() == 1
    assert flop_counts_3.total_count() == 0


def test_pause_flop_counting_nested():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        with PauseFlopCounting():
            with PauseFlopCounting():
                _ = cf1 + cf2  # should not be counted (doubly paused)
            _ = cf1 * cf2  # should not be counted (still inside outer pause)
        _ = cf1 / cf2  # should be counted (both pauses exited)

    # --- assert ------------------------------------------
    flop_counts = fcc.flop_counts()
    assert flop_counts.ADD == 0
    assert flop_counts.MUL == 0
    assert flop_counts.DIV == 1


def test_pause_flop_counting_restores_paused_state():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)

    # --- act ---------------------------------------------
    with FlopCountingContext() as fcc:
        THREAD_COUNTER.pause()
        with PauseFlopCounting():
            pass
        _ = cf1 + cf2  # should not be counted: counter was already paused before the with-block
        THREAD_COUNTER.resume()
        _ = cf1 * cf2  # should be counted

    # --- assert ------------------------------------------
    flop_counts = fcc.flop_counts()
    assert flop_counts.ADD == 0
    assert flop_counts.MUL == 1


def test_flop_counting_context_reentrant_same_instance():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)
    fcc = FlopCountingContext()

    # --- act ---------------------------------------------
    with fcc:
        _ = cf1 + cf2
        with fcc:  # re-entering the same instance
            _ = cf1 + cf2
        _ = cf1 + cf2  # still inside the outer block, so still counted

    # --- assert ------------------------------------------
    assert fcc.flop_counts().ADD == 3


def test_flop_counting_context_reentrant_keeps_math_patched_until_outermost_exit():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(4.0)
    fcc = FlopCountingContext()

    # --- act ---------------------------------------------
    with fcc:
        with fcc:
            pass
        _ = math.sqrt(cf1)  # the inner exit must not have unpatched math

    # --- assert ------------------------------------------
    # counting the sqrt at all proves math was still patched after the inner exit
    assert fcc.flop_counts().SQRT == 1


def test_flop_counting_context_sequential_reuse_accumulates_and_excludes_the_gap():
    # --- arrange -----------------------------------------
    cf1 = CountedFloat(1.0)
    cf2 = CountedFloat(2.0)
    fcc = FlopCountingContext()

    # --- act ---------------------------------------------
    with fcc:
        _ = cf1 + cf2
    _ = cf1 * cf2  # between the blocks: must not be counted
    with fcc:
        _ = cf1 + cf2

    # --- assert ------------------------------------------
    flop_counts = fcc.flop_counts()
    assert flop_counts.ADD == 2
    assert flop_counts.MUL == 0


@pytest.mark.parametrize("action", ["pause", "resume"])
def test_flop_counting_context_pause_resume_outside_with_block_raises(action: str):
    # --- arrange -----------------------------------------
    fcc = FlopCountingContext()

    # --- act / assert ------------------------------------
    with pytest.raises(RuntimeError, match=action):
        getattr(fcc, action)()  # never entered

    with fcc:
        pass

    with pytest.raises(RuntimeError, match=action):
        getattr(fcc, action)()  # already exited
