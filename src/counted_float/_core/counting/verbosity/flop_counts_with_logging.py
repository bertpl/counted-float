"""Counts target that logs the flops registered on it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .callsite import format_location, locate_call
from .output import VerbosityWriter

if TYPE_CHECKING:
    from counted_float._core.models import FlopCounts


# =================================================================================================
#  FlopCountsWithLogging
# =================================================================================================
class FlopCountsWithLogging:
    """Counts object that logs each flop registered on it, then forwards it to the real counts.

    While a thread counts verbosely, its increments are sent here instead of straight into its own
    FlopCounts -- the same redirection ``pause()`` uses to send them into a discard sink instead.
    Writing a count field logs the increment and then applies it to the wrapped counts, so counting
    sites keep executing the same ``<target>.<FIELD> += 1`` statement they execute when verbosity
    is off.  That is what makes verbosity free at level OFF: no counting site tests a flag of its
    own.

    Only writes are handled here.  Reading counts back goes to the wrapped FlopCounts directly, as
    the thread counter's read path does.
    """

    __slots__ = ("_counts", "_pending_rationale", "_writer")

    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self, counts: FlopCounts) -> None:
        """Wrap the counts that increments are forwarded to.

        Args:
            counts: The thread's real counts; this target logs on the way there and holds no
                counts of its own.
        """
        self._counts = counts
        self._writer = VerbosityWriter.shared()
        self._pending_rationale = ""

    # -------------------------------------------------------------------------
    #  Increment-target contract
    # -------------------------------------------------------------------------
    def note(self, rationale: str) -> None:
        """Render `rationale` on the line logged for the next flop registered here.

        Args:
            rationale: Short explanation of the counting rule being applied.
        """
        self._pending_rationale = rationale

    def __getattr__(self, name: str) -> int:
        """Read a count field from the wrapped counts.

        Only reached for attributes this object does not have itself, which is exactly the count
        fields -- its own live in ``__slots__``.  An unknown name raises, as it would on the
        wrapped counts, so a mistyped field is still caught at the counting site.

        Args:
            name: Name of the count field to read.

        Returns:
            The wrapped counts' current value for that field.
        """
        return getattr(self._counts, name)

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401 -- the name decides the type
        """Log a count field's increment, then apply it to the wrapped counts.

        ``target.FIELD += n`` reads through ``__getattr__`` and writes back through here, so a
        counting site's single increment statement becomes one log line plus the real increment.

        Args:
            name: Name of the count field being written, or of one of this object's own
                (underscore-prefixed) attributes, which are set as-is.
            value: The field's new value.
        """
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        counts = self._counts
        increment = value - getattr(counts, name)
        setattr(counts, name, value)
        rationale, self._pending_rationale = self._pending_rationale, ""
        self._writer.write_flop(name, increment, rationale, format_location(locate_call()))
