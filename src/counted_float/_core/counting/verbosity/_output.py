"""Rendering of verbose counting output to stderr."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

# --- column widths -----------------------------------
# Alignment does the structural work of the output, so the columns are fixed-width: the level tag
# and the operation are sized to their longest member (a flop type, or a math function that could
# not be counted), the count column to a four-digit bulk increment, and the rationale column to the
# longest explanation the counting rules produce.  The location closes each line, at whatever width
# it needs.  A longer-than-expected field pushes the rest of its line right rather than being
# truncated -- a misaligned line beats a lost message.
_LEVEL_WIDTH = 4
_OPERATION_WIDTH = 10
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
        self._write(("INFO", "dim cyan"), flop_type, f"+{count}", rationale, location)

    def write_uncounted(self, operation: str, consequence: str, location: str) -> None:
        """Log an operation that was seen but could not be counted.

        The count column stays empty: that nothing was counted is the point of the line.

        Args:
            operation: Name of the operation that could not be counted.
            consequence: Short statement of what the missing count costs.
            location: ``file.py:lineno`` of the user code that made the call.
        """
        # yellow is spent only on lines reporting that something is wrong
        self._write(("WARN", "yellow"), operation, "", consequence, location)

    def _write(self, level: tuple[str, str], operation: str, count: str, rationale: str, location: str) -> None:
        """Write one line, in the fixed columns every line shares.

        Args:
            level: The line's level tag and the style to render it in.
            operation: What the line is about — a flop type, or an operation that was not counted.
            count: How many flops were registered, rendered as-is; empty when none were.
            rationale: Short explanation, or empty when there is nothing to explain.
            location: ``file.py:lineno`` of the user code the line is about.
        """
        from rich.text import Text

        level_tag, level_style = level
        self._console.print(
            Text.assemble(
                (f"{level_tag:<{_LEVEL_WIDTH}}", level_style),
                "  ",
                # the column the eye scans, so it gets weight rather than a hue of its own
                (f"{operation:<{_OPERATION_WIDTH}}", "bold"),
                "  ",
                f"{count:<{_COUNT_WIDTH}}",
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
