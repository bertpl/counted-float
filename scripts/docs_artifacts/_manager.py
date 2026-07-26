"""Holds the set of derived files, and the two things anyone wants to do with them.

Checking and regenerating ask each artifact the same question — *what should you contain?* — and
differ only in what they do with the answer. Neither knows what kind of artifact it is holding,
which is the point: adding a kind is a `DerivedFile` subclass, never a branch in here.
"""

from __future__ import annotations

import dataclasses
import difflib
from typing import TYPE_CHECKING

from ._artifact import read_lf

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ._artifact import DerivedFile

# The one remedy, stated once: every staleness reported here is fixed the same way.
_REMEDY = "run `make regen-docs`"


# ==================================================================================================
#  Findings
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class Stale:
    """One committed file that no longer agrees with what it should be."""

    artifact: DerivedFile

    def describe(self) -> str:
        """How this staleness is shown to a reader."""
        raise NotImplementedError


@dataclasses.dataclass(frozen=True)
class StaleContent(Stale):
    """A file whose re-derived content differs from what is committed."""

    committed: str
    intended: str

    def describe(self) -> str:
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


# ==================================================================================================
#  DocsArtifactManager
# ==================================================================================================
class DocsArtifactManager:
    """The registry of derived files, and the operations over it.

    One instance owns the whole set, so a caller names the artifacts once and then asks for what it
    wants, rather than threading the registry through every call.
    """

    def __init__(self, artifacts: Sequence[DerivedFile]) -> None:
        """Take ownership of the artifact registry, in the order findings should be reported."""
        self._artifacts = artifacts

    # --------------------------------------------------------------------------
    #  Checking
    # --------------------------------------------------------------------------
    def check(self) -> list[Stale]:
        """Compare every producible artifact against what is committed.

        An artifact that cannot be produced on this machine is skipped rather than reported: the
        only answer available locally would be a false mismatch.

        Returns:
            One entry per stale file, in registry order; empty when everything is current.
        """
        stale: list[Stale] = []
        for artifact in self._artifacts:
            if not artifact.can_produce_here():
                continue
            if (finding := self._compare_content(artifact)) is not None:
                stale.append(finding)
        return stale

    def stale_report(self, stale: Sequence[Stale]) -> str:
        """The full stderr report for a set of findings: one description each, then the remedy."""
        described = "".join(f"{finding.describe()}\n" for finding in stale)
        return f"{described}stale generated docs content -- {_REMEDY}\n"

    @staticmethod
    def _compare_content(artifact: DerivedFile) -> StaleContent | None:
        """Re-derive one artifact's content and compare it against what is committed."""
        intended = artifact.intended_content()
        committed = read_lf(artifact.path) if artifact.path.exists() else ""
        if committed == intended:
            return None
        return StaleContent(artifact=artifact, committed=committed, intended=intended)

    # --------------------------------------------------------------------------
    #  Regenerating
    # --------------------------------------------------------------------------
    def regenerate(self) -> Regenerated:
        """Rewrite every producible artifact that is stale, leaving current ones untouched."""
        intended: dict[Path, str] = {}
        written: list[Path] = []
        for artifact in self._artifacts:
            if not artifact.can_produce_here():
                continue
            content = artifact.intended_content()
            intended[artifact.path] = content
            if not artifact.path.exists() or read_lf(artifact.path) != content:
                artifact.path.parent.mkdir(parents=True, exist_ok=True)
                artifact.path.write_text(content, encoding="utf-8", newline="\n")
                written.append(artifact.path)
        return Regenerated(intended=intended, written=written)
