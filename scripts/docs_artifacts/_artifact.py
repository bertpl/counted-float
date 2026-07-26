"""The `DerivedFile` hierarchy: one committed file that is generated rather than written.

`DerivedFile` is the abstract base. It defines the four questions the manager asks of every
committed file, and answers three of them with defaults:

  - `intended_content()` — abstract, and the only thing every subclass must implement. It is what
    the file *should* contain right now, re-derived from whatever the file is generated from.
  - `can_produce_here()` — whether this machine can answer the first question at all. Default True.
  - `readable(content)` — that content as it should appear in a diff. Default: unchanged.
  - `fingerprint()` — a hash of the file's inputs, for kinds that cannot be re-derived here at all.
    Default None, meaning "compare my content instead".

Three concrete subclasses, differing mainly in how they answer the first question:

  - **`MarkedBlockFile`** — an authored file with generated regions in it, between
    `<!-- BEGIN/END generated: name -->` markers. Its intended content is the *committed* file with
    each region replaced, so the hand-written prose around them survives by construction. One file
    can hold several regions, which is why this subclass holds a mapping rather than one generator.
  - **`GeneratedFile`** — a file with no authored part at all: its committed bytes *are* the
    generator's output, so its intended content is simply that output. It also overrides the other
    two defaults, since a whole-file generator may be unavailable on a given platform and its
    output may not be readable as it stands.
  - **`RenderedFile`** — a file built by external tooling whose bytes no machine reproduces
    identically. It cannot answer the first question at all, so it answers the fourth instead:
    `fingerprint()`, a hash of everything its bytes are a function of.

The first two are checked the same way — re-derive, compare. The third cannot be, which is why the
base carries a fingerprint question whose default is None: the manager asks both, and each subclass
answers whichever one it can.
"""

from __future__ import annotations

import abc
import dataclasses
import hashlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

_MARKER_RE = re.compile(r"<!-- (BEGIN|END) generated: ([a-z0-9-]+) -->")


def read_lf(file_path: Path) -> str:
    r"""Read a text file as UTF-8 with line endings normalized to \n.

    Windows CI checks out CRLF while every generator emits \n, so both the comparison and the
    rewrite happen in \n space regardless of what git put on disk.
    """
    return file_path.read_text(encoding="utf-8").replace("\r\n", "\n")


# ==================================================================================================
#  DerivedFile -- abstract base of the hierarchy
# ==================================================================================================
class DerivedFile(abc.ABC):
    """One committed file whose content is derived, and how to tell whether it is current.

    Subclasses implement `intended_content`; the other two answers have defaults that hold for the
    common case, so a new kind of file is a new subclass rather than a new branch in the manager.
    """

    def __init__(self, path: Path) -> None:
        """Bind the artifact to the committed file it describes."""
        self.path = path

    # --------------------------------------------------------------------------
    #  Manager interface
    # --------------------------------------------------------------------------
    @abc.abstractmethod
    def intended_content(self) -> str:
        """The content this file should hold, re-derived from its current inputs."""

    def can_produce_here(self) -> bool:
        """Whether this machine can produce the intended content at all.

        A file that cannot be produced here is never byte-compared, because the only honest answer
        available locally would be a false mismatch.
        """
        return True

    def readable(self, content: str) -> str:
        """This file's content as it should appear in a staleness diff.

        Defaults to the content itself; kinds whose committed bytes are unreadable (raw ANSI)
        override it, so a reader sees which *output* changed rather than which escape sequences.
        """
        return content

    def fingerprint(self) -> str | None:
        """A hash of everything this file is a function of, for files that cannot be re-derived here.

        None means the file is checked by re-deriving and comparing its content, which is strictly
        stronger — so a fingerprint exists only where that is impossible.
        """
        return None


# ==================================================================================================
#  MarkedBlockFile -- authored file with generated regions
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class MarkedBlock:
    """One generated region: the file it sits in, and what produces its content.

    Attributes:
        file: The authored file carrying this region's BEGIN/END markers.
        generate: Returns the region's content, without the marker lines.
    """

    file: Path
    generate: Callable[[], str]


class MarkedBlockFile(DerivedFile):
    """An authored file with one or more generated regions in it."""

    def __init__(self, path: Path, blocks: dict[str, Callable[[], str]]) -> None:
        """Bind the file to the generators for the regions it carries, by marker name."""
        super().__init__(path)
        self.blocks = blocks

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


def marked_block_files(registry: dict[str, MarkedBlock]) -> list[MarkedBlockFile]:
    """Group a `marker name -> MarkedBlock` registry into one artifact per file.

    Regions are registered individually because that is how they are authored and read, but the
    unit that gets compared against disk is the file they share.
    """
    by_file: dict[Path, dict[str, Callable[[], str]]] = {}
    for name, block in registry.items():
        by_file.setdefault(block.file, {})[name] = block.generate
    return [MarkedBlockFile(path=path, blocks=blocks) for path, blocks in by_file.items()]


# ==================================================================================================
#  GeneratedFile -- whole file, no authored part
# ==================================================================================================
class GeneratedFile(DerivedFile):
    """A whole file produced by a generator, whose committed bytes are that generator's output."""

    def __init__(
        self,
        path: Path,
        produce: Callable[[], str],
        producible_here: bool = True,
        as_readable: Callable[[str], str] | None = None,
    ) -> None:
        """Bind the file to its generator, plus the two overrides a whole-file kind may need.

        Args:
            path: The committed file.
            produce: Returns the full intended content.
            producible_here: False on a platform whose output would differ for reasons unrelated to
                staleness — see the terminal captures, which are not comparable against Windows.
            as_readable: Renders the content for a diff, when the raw bytes are not readable.
        """
        super().__init__(path)
        self.produce = produce
        self.producible_here = producible_here
        self.as_readable = as_readable

    def intended_content(self) -> str:
        """The generator's current output."""
        return self.produce()

    def can_produce_here(self) -> bool:
        """Whether this platform produces comparable output for this file."""
        return self.producible_here

    def readable(self, content: str) -> str:
        """The content as it should appear in a diff, per `as_readable`."""
        return content if self.as_readable is None else self.as_readable(content)


# ==================================================================================================
#  RenderedFile
# ==================================================================================================
class RenderedFile(DerivedFile):
    """A file built by external tooling, whose bytes are not reproducible across machines.

    Nothing here can be byte-compared: the renderer is absent in CI, and even where it is present
    its output differs by tool version and platform. So the file is checked against a hash of its
    inputs instead, which is platform-stable and needs no renderer to recompute.
    """

    def __init__(self, path: Path, inputs: Callable[[], Sequence[str]]) -> None:
        """Bind the file to a description of everything its bytes are a function of.

        Args:
            path: The committed file.
            inputs: Returns source content, the resolved render geometry, and the tool parameters,
                in a canonical, stable order.
        """
        super().__init__(path)
        self.inputs = inputs

    def intended_content(self) -> str:
        """Never called: a rendered file is checked by fingerprint, never by content."""
        raise NotImplementedError(f"{self.path.name} is checked by fingerprint, not by content")

    def can_produce_here(self) -> bool:
        """Always False — that is what makes this a fingerprinted artifact rather than a compared one."""
        return False

    def fingerprint(self) -> str:
        """A stable hash over this file's declared inputs."""
        digest = hashlib.sha256()
        for part in self.inputs():
            # length-prefixed so that concatenation can never make two different input lists collide
            digest.update(f"{len(part)}:".encode())
            digest.update(part.encode("utf-8"))
        return f"sha256:{digest.hexdigest()}"
