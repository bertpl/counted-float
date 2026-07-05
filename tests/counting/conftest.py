import pytest

from counted_float import FlopCountingContext
from counted_float._core.counting._global_counter import GLOBAL_COUNTER, GlobalFlopCounter


@pytest.fixture
def global_counter() -> GlobalFlopCounter:
    """
    Fixture giving direct access to the global flop counter, ensuring it is reset BEFORE & AFTER
    each test, with an active FlopCountingContext so the math-module patches are applied.

    Tests deliberately read the raw global counter instead of the context's reporting surface:
    this keeps each test focused on a single narrow scope of functionality (the context managers
    themselves are tested in their own right elsewhere).
    """

    # prepare
    GLOBAL_COUNTER.reset()

    # yield, with math patches active
    with FlopCountingContext():
        yield GLOBAL_COUNTER

    # cleanup
    GLOBAL_COUNTER.reset()
