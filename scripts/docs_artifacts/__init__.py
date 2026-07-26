"""Keeps the committed files that are generated from the library in step with what it produces.

Parts of the docs are not written by hand — they are produced from the library and committed
alongside it, which means they can quietly fall behind the code. This package is what notices.

Modules
-------

  - `_artifact` — the `DerivedFile` hierarchy: one class per kind of generated file.
  - `_manager` — `DocsArtifactManager`, holding a set of them and offering the only two operations
    there are: check them, or regenerate them.
  - `_ansi` — helpers for the files whose content is raw terminal output.

The `DerivedFile` hierarchy
---------------------------

One abstract base, one concrete class per kind of generated file. The base defines what the manager
is allowed to ask; each subclass answers in its own terms, so the manager never branches on kind::

    DerivedFile                (abstract: defines the questions)
    ├── MarkedBlockFile        an authored file with generated regions in it
    └── GeneratedFile          a whole file that is nothing but generator output

What the base asks, and what differs between the children:

  - **`intended_content()`** — abstract, and the only difference that matters.
    `MarkedBlockFile` returns the *committed* file with each marked region replaced, preserving the
    hand-written prose around them; `GeneratedFile` returns its generator's output outright, because
    there is no authored part to preserve.
  - **`can_produce_here()`** — whether this machine can produce that content at all. Only
    `GeneratedFile` overrides it, since a whole-file generator can be platform-dependent (the
    terminal captures are not comparable against Windows). A file that answers False is skipped
    rather than reported stale, because the only local answer would be a false mismatch.
  - **`readable(content)`** — how the content should appear in a diff. Only `GeneratedFile`
    overrides it, for the captures whose raw ANSI is unreadable as it stands.

Two flat value types sit beside the hierarchy and are deliberately not part of it: `MarkedBlock`
(one registered region: its file plus its generator) and `RegenerationOutcome` (what a regeneration
pass produced). They carry data, answer no questions, and have no subclasses.

Only the machinery lives here. *Which* files exist and how each one is produced is content, and
stays with the generators in `generate_docs_content.py`.
"""

from ._ansi import capture_env, crop_ansi_line, strip_ansi
from ._artifact import (
    DerivedFile,
    GeneratedFile,
    MarkedBlock,
    MarkedBlockFile,
    marked_block_files,
    read_lf,
    rewrite_marked_blocks,
)
from ._manager import DocsArtifactManager, RegenerationOutcome, StaleFile

__all__ = [
    "DerivedFile",
    "DocsArtifactManager",
    "GeneratedFile",
    "MarkedBlock",
    "MarkedBlockFile",
    "RegenerationOutcome",
    "StaleFile",
    "capture_env",
    "crop_ansi_line",
    "marked_block_files",
    "read_lf",
    "rewrite_marked_blocks",
    "strip_ansi",
]
