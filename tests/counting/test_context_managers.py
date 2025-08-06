import pytest

from counted_float._core.counting._context_managers import FlopCountingContext, PauseFlopCounting
from counted_float._core.counting._counted_float import CountedFloat


# =================================================================================================
#  FlopCountingContext
# =================================================================================================
def test_flop_counting_context_construction():
    fcc = FlopCountingContext()


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
    with FlopCountingContext() as fcc1:
        with FlopCountingContext() as fcc2:
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
    with FlopCountingContext() as fcc1:
        with FlopCountingContext() as fcc2:
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
