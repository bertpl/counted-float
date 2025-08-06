import pytest

from counted_float._core.counting._global_counter import GLOBAL_COUNTER, GlobalFlopCounter


@pytest.fixture
def global_counter() -> GlobalFlopCounter:
    """Fixture that gives access to the global flop counter, ensuring it is reset BEFORE & AFTER each test."""

    # prepare
    GLOBAL_COUNTER.reset()

    # yield
    yield GLOBAL_COUNTER

    # cleanup
    GLOBAL_COUNTER.reset()
