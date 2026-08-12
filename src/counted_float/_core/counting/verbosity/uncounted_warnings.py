"""Warnings about operations that were seen but could not be counted."""

from __future__ import annotations

from .callsite import format_location, locate_call
from .output import VerbosityWriter

# Call sites reported so far, for the lifetime of the process.  Each entry pairs the operation that
# could not be counted with the exact place it was called from -- ("erf", ("/proj/my_algo.py", 42))
# -- so one operation called from two places is two findings, while a call site inside a loop stays
# one however often it runs.
#
# A finding belongs to a source line rather than to a run or a thread, so reporting it once is
# enough -- which is what keeps this level usable on a full run instead of only on a snippet
# (Python's own warnings default to the same once-per-location rule).  Shared across threads
# without a lock: two threads racing on one site can at worst report it twice.
_reported: set[tuple[str, tuple[str, int]]] = set()


def warn_uncounted_call(operation: str, consequence: str) -> None:
    """Report an operation that touched a counted value without being counted.

    Args:
        operation: Name of the operation that could not be counted, e.g. ``"erf"``.
        consequence: Short statement of what that costs the count, e.g. that the result comes
            back as a plain float and stops counting downstream.
    """
    # deduplicated on the raw location, so that a call site already reported costs a tuple and a
    # set lookup -- rendering it (and walking pathlib to do so) happens once, on the first report
    location = locate_call()
    key = (operation, location)
    if key in _reported:
        return
    _reported.add(key)
    VerbosityWriter.shared().write_uncounted(operation, consequence, format_location(location))
