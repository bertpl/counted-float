"""Operations that were seen but could not be counted are reported here.

At ERROR verbosity the report is an exception; at WARNING and INFO it is a line on stderr.
"""

from __future__ import annotations

from .callsite import format_location, locate_call
from .levels import Verbosity
from .output import VerbosityWriter

# Call sites written to stderr so far, for the lifetime of the process.  Each entry pairs the
# operation that could not be counted with the exact place it was called from --
# ("erf", ("/proj/my_algo.py", 42)) -- so one operation called from two places is two findings,
# while a call site inside a loop stays one however often it runs.
#
# A finding belongs to a source line rather than to a run or a thread, so reporting it once is
# enough -- which is what keeps WARNING usable on a full run instead of only on a snippet
# (Python's own warnings default to the same once-per-location rule).  Shared across threads
# without a lock: two threads racing on one site can at worst report it twice.
_reported: set[tuple[str, tuple[str, int]]] = set()


class UncountedOperationError(RuntimeError):
    """An operation touched a counted value without being counted, at ERROR verbosity.

    Attributes:
        operation: Name of the operation that could not be counted, e.g. ``"frexp"``.
        consequence: Short statement of what the missing count costs.
        location: ``file.py:lineno`` of the user code that made the call.
    """

    def __init__(self, operation: str, consequence: str, location: str) -> None:
        # the fields are RuntimeError's args, so that the error survives pickling: unpickling calls
        # the class with its args, and multiprocessing pickles an error to send it from a worker
        # process back to its parent
        super().__init__(operation, consequence, location)
        self.operation = operation
        self.consequence = consequence
        self.location = location

    def __str__(self) -> str:
        """Name the operation, the call site, and what the missing count costs."""
        return f"{self.operation} at {self.location} could not be counted: {self.consequence}"


def report_uncounted_operation(level: Verbosity, operation: str, consequence: str) -> None:
    """Report an operation that touched a counted value without being counted.

    At ERROR this raises, on every call: a test that reaches the operation has to fail, even when
    an earlier test already raised at the same call site, or WARNING already reported it.  At
    WARNING and INFO it writes a line, once per call site for the lifetime of the process.

    Args:
        level: The calling thread's verbosity level; never OFF, because a thread at OFF reports
            nothing.
        operation: Name of the operation that could not be counted, e.g. ``"erf"``.
        consequence: Short statement of what that costs the count, e.g. that the result comes
            back as a plain float and stops counting downstream.

    Raises:
        UncountedOperationError: If `level` is ERROR.
    """
    location = locate_call()
    if level is Verbosity.ERROR:
        raise UncountedOperationError(operation, consequence, format_location(location))
    # deduplicated on the raw location, so that a call site already reported costs a tuple and a
    # set lookup -- rendering it (and walking pathlib to do so) happens once, on the first report
    key = (operation, location)
    if key in _reported:
        return
    _reported.add(key)
    VerbosityWriter.shared().write_uncounted(operation, consequence, format_location(location))
