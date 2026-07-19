"""Resolution of the user-code location that triggered a counted flop."""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE = "counted_float"
_PACKAGE_PREFIX = "counted_float."
_UNKNOWN = "<unknown>"


def resolve_callsite() -> str:
    """Return ``file.py:lineno`` for the innermost stack frame outside this package.

    Walks outward past the counting machinery's own frames (operators, ``math`` replacements, the
    logging target) so the reported location is the expression the user wrote rather than the
    internals that counted it.  Only the file's base name is reported: verbose counting is a
    microscope for small snippets, where a full path is noise.

    Returns:
        ``file.py:lineno``, or ``<unknown>`` when no frame outside this package is on the stack.
        The fallback is there to make the walk fail-safe — there is always a string to report —
        rather than to describe a situation callers will meet: the entry module (``__main__``,
        pytest, a notebook) is always a frame outside the package, so the only realistic way in
        is the package driving counted code itself, e.g. in its own tests.
    """
    frame = sys._getframe(1)  # noqa: SLF001 -- the documented way to walk the Python stack
    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        if module_name != _PACKAGE and not module_name.startswith(_PACKAGE_PREFIX):
            return f"{Path(frame.f_code.co_filename).name}:{frame.f_lineno}"
        frame = frame.f_back
    return _UNKNOWN
