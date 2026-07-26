"""ANSI-aware text helpers shared by the capture and rendering paths.

Terminal captures are committed as raw ANSI, so cropping them has to count *visible* columns
rather than characters, and showing them in a diff has to strip the escapes first.
"""

from __future__ import annotations

import os
import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove all ANSI style sequences from `text`."""
    return _ANSI_RE.sub("", text)


def crop_ansi_line(line: str, width: int) -> str:
    """Crop one line to `width` *visible* columns, keeping every ANSI escape.

    Escapes count zero columns, so styling state stays balanced across the cut. A line that
    actually lost content gets a reset plus a dim ellipsis appended.
    """
    out: list[str] = []
    visible = 0
    pos = 0
    truncated = False
    for match in _ANSI_RE.finditer(line):
        for ch in line[pos : match.start()]:
            if visible >= width:
                truncated = True
                break
            out.append(ch)
            visible += 1
        out.append(match.group())
        pos = match.end()
    for ch in line[pos:]:
        if visible >= width:
            truncated = True
            break
        out.append(ch)
        visible += 1
    result = "".join(out)
    if truncated and line.strip():
        result += "\x1b[0m\x1b[2m …\x1b[0m"
    return result


def capture_env(columns: int) -> dict[str, str]:
    """Environment that makes rich emit truecolor ANSI at a fixed width without a real TTY."""
    # PYTHONUTF8 keeps the child's stdout/stderr UTF-8 on Windows, whose default locale
    # encoding cannot represent the tree's box-drawing characters
    return os.environ | {
        "COLUMNS": str(columns),
        "FORCE_COLOR": "1",
        "COLORTERM": "truecolor",
        "PYTHONUTF8": "1",
    }
