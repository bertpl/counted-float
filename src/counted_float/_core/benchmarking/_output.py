"""Centralized console for all benchmark progress output.

A single module-global rich Console funnels every benchmark print, so verbosity is
governed in exactly one place -- its ``quiet`` flag -- rather than by per-call guards
scattered across the suite, runner, and entry points. This mirrors the process-global
model the FLOP counter already uses; thread-safety is a documented non-goal, so a
shared mutable console is an accepted trade-off.

Markup and highlighting are disabled so the console is a faithful plain-text sink:
existing output contains literal square brackets that rich markup would otherwise try
to parse as style tags.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console

console = Console(markup=False, highlight=False)


@contextmanager
def output_quiet(quiet: bool) -> Iterator[None]:
    """Set the shared console's quiet flag for the duration of the block, restoring it on exit.

    Args:
        quiet: When True, silence all console output within the block.
    """
    previous = console.quiet
    console.quiet = quiet
    try:
        yield
    finally:
        console.quiet = previous
