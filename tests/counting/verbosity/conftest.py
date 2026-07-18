import pytest


@pytest.fixture
def logged_lines(capsys):
    """Return a reader for the non-empty lines logged to stderr so far."""

    def read() -> list[str]:
        return [line for line in capsys.readouterr().err.splitlines() if line.strip()]

    return read
