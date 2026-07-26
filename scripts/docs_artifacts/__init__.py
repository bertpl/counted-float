"""Keeps the committed files that are generated from the library in step with what it produces.

Parts of the docs are not written by hand — they are produced from the library and committed
alongside it, which means they can quietly fall behind the code. This package is what notices.

  - `_artifact` — what a derived file is: where it lives, how its intended content is produced,
    and how it should read in a diff. One subclass per kind of file.
  - `_manager` — `DocsArtifactManager`, holding the set of them and offering the only two
    operations there are: check them, or regenerate them.
  - `_ansi` — helpers for the files whose content is raw terminal output.

Only the machinery lives here. *Which* files exist and how each one is produced is content, and
stays with the generators in `generate_docs_content.py`.
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
from ._manager import DocsArtifactManager, Regenerated, Stale, StaleContent

__all__ = [
    "DerivedFile",
    "DocsArtifactManager",
    "GeneratedFile",
    "MarkedBlockFile",
    "Regenerated",
    "Stale",
    "StaleContent",
    "capture_env",
    "crop_ansi_line",
    "marked_block_files",
    "read_lf",
    "rewrite_marked_blocks",
    "strip_ansi",
]
