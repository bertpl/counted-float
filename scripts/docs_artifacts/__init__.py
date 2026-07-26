"""Freshness machinery for the committed files that are derived from the library.

The kind-agnostic half of `generate_docs_content.py`: what a derived file is (`_artifact`) and the
single loop that checks or rewrites a set of them (`_driver`). What those files actually *are* —
which docs blocks exist, which screenshots exist, how each is produced — is content, and lives with
the generators in the script itself.
"""

from ._ansi import capture_env, crop_ansi_line, strip_ansi
from ._artifact import (
    DerivedFile,
    GeneratedFile,
    MarkedBlockFile,
    marked_block_files,
    read_lf,
    rewrite_marked_blocks,
)
from ._driver import REMEDY, Regenerated, StaleFile, check, format_stale_report, regenerate

__all__ = [
    "REMEDY",
    "DerivedFile",
    "GeneratedFile",
    "MarkedBlockFile",
    "Regenerated",
    "StaleFile",
    "capture_env",
    "check",
    "crop_ansi_line",
    "format_stale_report",
    "marked_block_files",
    "read_lf",
    "regenerate",
    "rewrite_marked_blocks",
    "strip_ansi",
]
