import pytest

from counted_float import FlopCountingContext
from counted_float._core.counting._thread_counter import THREAD_COUNTER, ThreadLocalFlopCounter


@pytest.fixture
def thread_counter() -> ThreadLocalFlopCounter:
    """
    Fixture giving direct access to the calling thread's flop counter, ensuring it is reset
    BEFORE & AFTER each test, with an active FlopCountingContext so the math-module patches
    are applied.

    Tests deliberately read the raw thread counter instead of the context's reporting surface:
    this keeps each test focused on a single narrow scope of functionality (the context managers
    themselves are tested in their own right elsewhere).
    """

    # prepare
    THREAD_COUNTER.reset()

    # yield, with math patches active
    with FlopCountingContext():
        yield THREAD_COUNTER

    # cleanup
    THREAD_COUNTER.reset()
