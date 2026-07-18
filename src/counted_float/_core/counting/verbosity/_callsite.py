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
        ``file.py:lineno``, or ``<unknown>`` when every frame on the stack belongs to this
        package — which happens when counted code is driven from a C-level caller that has no
        Python frame of its own.
    """
    frame = sys._getframe(1)  # noqa: SLF001 -- the documented way to walk the Python stack
    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        if module_name != _PACKAGE and not module_name.startswith(_PACKAGE_PREFIX):
            return f"{Path(frame.f_code.co_filename).name}:{frame.f_lineno}"
        frame = frame.f_back
    return _UNKNOWN
