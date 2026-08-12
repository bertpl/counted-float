import pytest

from counted_float._core.counting.verbosity import uncounted_warnings


@pytest.fixture(autouse=True)
def forget_reported_calls():
    """Start each test with nothing reported yet.

    The record of reported call sites is process-wide and deliberately never reset at runtime, so
    tests have to clear it themselves to stay independent of one another.
    """

    uncounted_warnings._reported.clear()


@pytest.fixture
def logged_lines(capsys):
    """Return a reader for the non-empty lines logged to stderr so far."""

    def read() -> list[str]:
        return [line for line in capsys.readouterr().err.splitlines() if line.strip()]

    return read
