"""What a committed, derived file is, and how each kind knows its own intended content.

Everything the docs show that is *derived* from the library is one of two shapes:

  - **marked regions inside an authored file** — a block between `<!-- BEGIN/END generated: name -->`
    markers. Regeneration rewrites only those regions; the surrounding prose is hand-written, and
    several regions can share one file.
  - **a whole generated file** — the terminal captures, whose committed bytes *are* the generator's
    output.

Both are checked the same way: re-derive the file's intended content and compare it to what is
committed. They differ only in how that intended content is arrived at, which is exactly what the
two `DerivedFile` implementations below encapsulate — so the driver never asks which kind it holds.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_MARKER_RE = re.compile(r"<!-- (BEGIN|END) generated: ([a-z0-9-]+) -->")


def read_lf(file_path: Path) -> str:
    r"""Read a text file as UTF-8 with line endings normalized to \n.

    Windows CI checks out CRLF while every generator emits \n, so both the comparison and the
    rewrite happen in \n space regardless of what git put on disk.
    """
    return file_path.read_text(encoding="utf-8").replace("\r\n", "\n")


# ==================================================================================================
#  DerivedFile
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class DerivedFile:
    """One committed file whose content is derived, and how to tell whether it is current.

    Subclasses supply `intended_content`; everything else the driver needs is answered here, so a
    new kind of artifact is a new subclass rather than a new branch in the driver.
    """

    path: Path

    # --------------------------------------------------------------------------
    #  Driver interface
    # --------------------------------------------------------------------------
    def intended_content(self) -> str:
        """The content this file should hold, re-derived from its current inputs."""
        raise NotImplementedError

    def can_produce_here(self) -> bool:
        """Whether this machine can produce the intended content at all.

        A file that cannot be produced here is neither checked nor rewritten, because the only
        honest answer available locally would be a false mismatch.
        """
        return True

    def readable(self, content: str) -> str:
        """This file's content as it should appear in a staleness diff.

        Defaults to the content itself; kinds whose committed bytes are unreadable (raw ANSI)
        override it, so a reader sees which *output* changed rather than which escape sequences.
        """
        return content


# ==================================================================================================
#  MarkedBlockFile
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class MarkedBlockFile(DerivedFile):
    """An authored file with one or more generated regions in it.

    Attributes:
        blocks: Marker name -> the generator producing that region's content.
    """

    blocks: dict[str, Callable[[], str]]

    def intended_content(self) -> str:
        """The committed file with every marked region replaced by freshly generated content."""
        return rewrite_marked_blocks(
            read_lf(self.path),
            self.path,
            {name: generate() for name, generate in self.blocks.items()},
        )


def rewrite_marked_blocks(text: str, file_path: Path, replacements: dict[str, str]) -> str:
    """Replace every marked region in `text` with its regenerated content.

    Markers must be well-formed: BEGIN/END strictly alternating, names matching per pair, no
    nesting, every found name known, and every expected name found — anything else raises, so a
    malformed or half-deleted marker can never silently freeze a block.

    Args:
        text: The file's current content.
        file_path: Where the text came from, for error messages and registry validation.
        replacements: block name -> regenerated content (without the marker lines).

    Returns:
        The rewritten file content.
    """
    out: list[str] = []
    pos = 0
    open_name: str | None = None
    seen: set[str] = set()
    for match in _MARKER_RE.finditer(text):
        kind, name = match.groups()
        if kind == "BEGIN":
            if open_name is not None:
                raise ValueError(f"{file_path}: nested BEGIN marker '{name}' inside '{open_name}'")
            if name not in replacements:
                raise ValueError(f"{file_path}: marker '{name}' has no registered generator")
            if name in seen:
                raise ValueError(f"{file_path}: duplicate marker '{name}'")
            open_name = name
            seen.add(name)
            out.append(text[pos : match.end()])
            out.append("\n" + replacements[name] + "\n")
        else:
            if open_name is None:
                raise ValueError(f"{file_path}: END marker '{name}' without a BEGIN")
            if name != open_name:
                raise ValueError(f"{file_path}: END marker '{name}' closes BEGIN '{open_name}'")
            open_name = None
            out.append(match.group())
        pos = match.end()
    if open_name is not None:
        raise ValueError(f"{file_path}: BEGIN marker '{open_name}' is never closed")
    missing = set(replacements) - seen
    if missing:
        raise ValueError(f"{file_path}: expected markers not found: {sorted(missing)}")
    out.append(text[pos:])
    return "".join(out)


def marked_block_files(registry: dict[str, tuple[Path, Callable[[], str]]]) -> list[MarkedBlockFile]:
    """Group a flat `name -> (file, generator)` registry into one artifact per file.

    Blocks are registered individually because that is how they are authored and read, but the
    unit that gets compared against disk is the file they share.
    """
    by_file: dict[Path, dict[str, Callable[[], str]]] = {}
    for name, (file_path, generate) in registry.items():
        by_file.setdefault(file_path, {})[name] = generate
    return [MarkedBlockFile(path=path, blocks=blocks) for path, blocks in by_file.items()]


# ==================================================================================================
#  GeneratedFile
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class GeneratedFile(DerivedFile):
    """A whole file produced by a generator, whose committed bytes are that generator's output.

    Attributes:
        produce: Returns the full intended content.
        producible_here: False on a platform whose output would differ for reasons unrelated to
            staleness — see the terminal captures, which are not comparable against Windows.
        as_readable: Renders the content for a staleness diff, when the raw bytes are not readable.
    """

    produce: Callable[[], str]
    producible_here: bool = True
    as_readable: Callable[[str], str] | None = None

    def intended_content(self) -> str:
        """The generator's current output."""
        return self.produce()

    def can_produce_here(self) -> bool:
        """Whether this platform produces comparable output for this file."""
        return self.producible_here

    def readable(self, content: str) -> str:
        """The content as it should appear in a diff, per `as_readable`."""
        return content if self.as_readable is None else self.as_readable(content)
