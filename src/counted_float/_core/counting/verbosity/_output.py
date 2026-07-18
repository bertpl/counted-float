"""Rendering of verbose counting output to stderr."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

# --- column widths -----------------------------------
# Alignment does the structural work of the output, so the columns are fixed-width: the level tag
# and the flop type are sized to their longest member, the count column to a four-digit bulk
# increment, and the rationale column to the longest rationale the counting rules produce.  The
# location closes each line, at whatever width it needs.  A longer-than-expected field pushes the
# rest of its line right rather than being truncated -- a misaligned line beats a lost message.
_LEVEL_WIDTH = 4
_FLOP_TYPE_WIDTH = 10
_COUNT_WIDTH = 5
_RATIONALE_WIDTH = 40


# =================================================================================================
#  VerbosityWriter
# =================================================================================================
class VerbosityWriter:
    """Writes one line per counting event to stderr.

    Output goes through a rich Console, which handles ``NO_COLOR`` and non-terminal streams by
    itself, so the color scheme stays decorative: every line reads the same uncolored.
    """

    # one writer per process, so that rich's own output lock serializes the lines logged by
    # concurrently counting threads instead of letting them interleave mid-line
    _shared: VerbosityWriter | None = None
    _shared_lock = threading.Lock()

    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        # imported here rather than at module level, so that importing this module -- which the
        # counting core does, whatever the verbosity level -- costs nothing until a context
        # actually asks for output
        from rich.console import Console

        # soft_wrap: these lines are tabular, so they must not be wrapped or cropped to the
        # terminal width
        self._console: Console = Console(stderr=True, highlight=False, soft_wrap=True)

    @classmethod
    def shared(cls) -> VerbosityWriter:
        """Return the process-wide writer, creating it on first use."""
        with cls._shared_lock:
            if cls._shared is None:
                cls._shared = cls()
            return cls._shared

    # -------------------------------------------------------------------------
    #  Writing events
    # -------------------------------------------------------------------------
    def write_flop(self, flop_type: str, count: int, rationale: str, location: str) -> None:
        """Log a registered flop count.

        Args:
            flop_type: Name of the flop type that was counted.
            count: How many of them the single counting statement registered.
            rationale: Short explanation of a counting rule that is not self-evident from the
                source expression; empty when there is nothing to explain.
            location: ``file.py:lineno`` of the user code that triggered the count.
        """
        from rich.text import Text

        self._console.print(
            Text.assemble(
                (f"{'INFO':<{_LEVEL_WIDTH}}", "dim cyan"),
                "  ",
                # the column the eye scans, so it gets weight rather than a hue of its own
                (f"{flop_type:<{_FLOP_TYPE_WIDTH}}", "bold"),
                "  ",
                f"{f'+{count}':<{_COUNT_WIDTH}}",
                "  ",
                (f"{rationale:<{_RATIONALE_WIDTH}}", "dim"),
                "  ",
                *_location_spans(location),
            )
        )


# =================================================================================================
#  Helpers
# =================================================================================================
def _location_spans(location: str) -> tuple[tuple[str, str], ...]:
    """Split ``file.py:42`` into a dim path span and a normal-intensity line-number span.

    The line number is what a reader jumps to, so it keeps full intensity while the file name
    around it recedes.

    Args:
        location: A ``file.py:lineno`` location, or any string without a line number.

    Returns:
        Styled spans ready to pass to rich's ``Text.assemble``.
    """
    file_name, separator, line_number = location.rpartition(":")
    if not separator:
        return ((location, "dim"),)
    return ((f"{file_name}:", "dim"), (line_number, "default"))
