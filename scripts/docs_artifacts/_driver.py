"""The one loop over every derived file: check it, or rewrite it.

Both modes ask each artifact the same question — *what should you contain?* — and differ only in
what they do with the answer. Nothing here knows what kind of artifact it is holding, which is the
point: adding a kind is a `DerivedFile` subclass, never a branch in this file.
"""

from __future__ import annotations

import dataclasses
import difflib
from typing import TYPE_CHECKING

from ._artifact import read_lf

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from ._artifact import DerivedFile

# The one remedy, stated in one place: every staleness this driver reports is fixed the same way.
REMEDY = "run `make regen-docs`"


# ==================================================================================================
#  Checking
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class StaleFile:
    """One committed file that disagrees with what its generator now produces."""

    artifact: DerivedFile
    committed: str
    intended: str

    def diff(self) -> str:
        """A unified diff of what changed, rendered through the artifact's readable form."""
        return "\n".join(
            difflib.unified_diff(
                self.artifact.readable(self.committed).splitlines(),
                self.artifact.readable(self.intended).splitlines(),
                lineterm="",
                n=1,
                fromfile=f"{self.artifact.path.name} (committed)",
                tofile=f"{self.artifact.path.name} (regenerated)",
            )
        )


def check(artifacts: Iterable[DerivedFile]) -> list[StaleFile]:
    """Compare every producible artifact against what is committed.

    Returns:
        One entry per stale file, in registry order; empty when everything is current.
    """
    stale: list[StaleFile] = []
    for artifact in artifacts:
        if not artifact.can_produce_here():
            continue
        intended = artifact.intended_content()
        committed = read_lf(artifact.path) if artifact.path.exists() else ""
        if committed != intended:
            stale.append(StaleFile(artifact=artifact, committed=committed, intended=intended))
    return stale


def format_stale_report(stale: Sequence[StaleFile]) -> str:
    """The full stderr report for a set of stale files: one diff each, then the remedy."""
    return "".join(f"{entry.diff()}\n" for entry in stale) + f"stale generated docs content -- {REMEDY}\n"


# ==================================================================================================
#  Regenerating
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class Regenerated:
    """The outcome of a regeneration pass.

    Attributes:
        intended: Every producible artifact's fresh content, by path — including files that were
            already current, since downstream steps consume the content rather than re-reading it.
        written: The paths actually rewritten, in registry order.
    """

    intended: dict[Path, str]
    written: list[Path]


def regenerate(artifacts: Iterable[DerivedFile]) -> Regenerated:
    """Rewrite every producible artifact that is stale, leaving current ones untouched."""
    intended: dict[Path, str] = {}
    written: list[Path] = []
    for artifact in artifacts:
        if not artifact.can_produce_here():
            continue
        content = artifact.intended_content()
        intended[artifact.path] = content
        if not artifact.path.exists() or read_lf(artifact.path) != content:
            artifact.path.parent.mkdir(parents=True, exist_ok=True)
            artifact.path.write_text(content, encoding="utf-8", newline="\n")
            written.append(artifact.path)
    return Regenerated(intended=intended, written=written)
