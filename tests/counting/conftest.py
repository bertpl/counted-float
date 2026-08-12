import math

import pytest

from counted_float import FlopCountingContext
from counted_float._core.counting import math_patching
from counted_float._core.counting.thread_counter import (
    _TLS,
    THREAD_COUNTER,
    ThreadLocalFlopCounter,
    _create_thread_state,
)

# Shared by the machinery and counting halves of the math-patching tests; defined here so both
# reach them at collection time (they key `@pytest.mark.parametrize` decorators).
PATCHED_FUNCTION_NAMES = sorted(math_patching._PATCHES.keys())

# captured at import of this conftest, i.e. with no counting context active anywhere
STDLIB_MATH_FUNCTIONS = {name: getattr(math, name) for name in PATCHED_FUNCTION_NAMES}


@pytest.fixture
def incr_flop():
    """Provide the increment call that the packaged code deliberately does not have.

    Production counting sites inline their increments -- a method call costs about as much as the
    increment itself (see the thread_counter module docstring) -- so ThreadLocalFlopCounter offers
    no increment API for tests to borrow.  Tests that want to register a flop without routing it
    through CountedFloat arithmetic use this helper instead.  It reproduces the production
    increment pattern exactly: a write through the thread's counts alias, with the lazy-init
    handler for a thread's first counted op -- so whatever target the alias points at (the live
    counts, the discard sink, a logging target) is exercised the same way real counting sites
    exercise it.
    """

    def incr(field: str, n: int = 1) -> None:
        try:
            counts = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            counts = _create_thread_state()
        setattr(counts, field, getattr(counts, field) + n)

    return incr


@pytest.fixture(autouse=True)
def restore_verbosity():
    """Restore the worker thread's verbosity level after each test.

    Verbosity is thread state that outlives a test: one that sets it directly (or fails inside a
    context before it is restored) would otherwise leave every later test in the same worker
    logging its counts.
    """

    previous = THREAD_COUNTER.verbosity()
    yield
    THREAD_COUNTER.set_verbosity(previous)


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
