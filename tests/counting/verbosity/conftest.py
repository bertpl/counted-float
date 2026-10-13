import math

import pytest

from counted_float._core.counting import math_patching
from counted_float._core.counting.verbosity import uncounted_operations

# Shared by the WARNING and ERROR tests of the uncounted math functions; defined here so both reach
# them at collection time (they key `@pytest.mark.parametrize` decorators).
UNCOUNTED_FUNCTION_NAMES = sorted(math_patching._UNCOUNTED_MATH)

# what each of them needs after its first (counted) argument
EXTRA_ARGUMENTS = {"ldexp": (2,), "nextafter": (3.0,)}


@pytest.fixture(autouse=True)
def forget_reported_calls():
    """Start each test with nothing reported yet.

    The record of reported call sites is process-wide and deliberately never reset at runtime, so
    tests have to clear it themselves to stay independent of one another.
    """

    uncounted_operations._reported.clear()


@pytest.fixture
def logged_lines(capsys):
    """Return a reader for the non-empty lines logged to stderr so far."""

    def read() -> list[str]:
        return [line for line in capsys.readouterr().err.splitlines() if line.strip()]

    return read


@pytest.fixture
def make_probe_wrapper(monkeypatch):
    """Build wrappers for fake math functions that record their delegated calls.

    Removing the reporting patches restores everything in _uncounted_originals onto the math
    module, so a probe entry leaks a new `math.<probe>` attribute the monkeypatch teardown does
    not know about; the fixture deletes those on the way out.
    """
    probe_names: list[str] = []

    def make(name: str, delegate_calls: list):
        def original(*args: object, **kwargs: object) -> str:
            delegate_calls.append((args, kwargs))
            return "delegated"

        monkeypatch.setitem(math_patching._uncounted_originals, name, original)
        probe_names.append(name)
        return math_patching._make_uncounted_wrapper(name, f"{name} consequence")

    yield make
    for name in probe_names:
        if hasattr(math, name):
            delattr(math, name)
