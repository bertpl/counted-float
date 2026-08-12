"""Resolution of the user-code location that triggered a counted flop.

Locating a call and rendering it are separate steps on purpose: warnings are deduplicated per call
site, so they locate every call but render only the first from each — and rendering is the
expensive half.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE = "counted_float"
_PACKAGE_PREFIX = "counted_float."
_UNKNOWN = "<unknown>"

# Stands in for a call that could not be attributed to user code, so that the walk is fail-safe and
# always has a location to report.  It is not a situation a caller of the library produces: reaching
# it means no frame outside this package was on the stack, and the entry module (__main__, pytest, a
# notebook) is always one.  The only realistic way in is the package driving counted code itself,
# e.g. while its own tests run.
UNKNOWN_LOCATION = (_UNKNOWN, 0)


def locate_call() -> tuple[str, int]:
    """Return the ``(file path, line number)`` of the innermost stack frame outside this package.

    Walks outward past the counting machinery's own frames (operators, ``math`` replacements, the
    logging target) so the location is the expression the user wrote rather than the internals
    that counted it.  Nothing is formatted here: this runs per call, while rendering does not.

    Returns:
        The frame's file path and line number, or `UNKNOWN_LOCATION` when every frame on the
        stack belongs to this package — see that constant for when that can happen.
    """
    frame = sys._getframe(1)  # noqa: SLF001 -- the documented way to walk the Python stack
    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        if module_name != _PACKAGE and not module_name.startswith(_PACKAGE_PREFIX):
            return frame.f_code.co_filename, frame.f_lineno
        frame = frame.f_back
    return UNKNOWN_LOCATION


def format_location(location: tuple[str, int]) -> str:
    """Render a located call as ``file.py:lineno``.

    Only the file's base name is kept: verbose counting is a microscope for small snippets, where
    a full path is noise.

    Args:
        location: A ``(file path, line number)`` pair, as returned by `locate_call`.

    Returns:
        ``file.py:lineno``, or ``<unknown>`` for a call with no user frame behind it.
    """
    file_path, line_number = location
    if file_path == _UNKNOWN:
        return _UNKNOWN
    return f"{Path(file_path).name}:{line_number}"
