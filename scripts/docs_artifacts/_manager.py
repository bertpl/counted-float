"""Holds the set of derived files, and the two things anyone wants to do with them.

Checking and regenerating ask each artifact the same question — *what should you contain?* — and
differ only in what they do with the answer. Neither knows what kind of artifact it is holding,
which is the point: adding a kind is a `DerivedFile` subclass, never a branch in here.
"""

from __future__ import annotations

import abc
import dataclasses
import difflib
from typing import TYPE_CHECKING

from ._artifact import read_lf
from ._manifest import Manifest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ._artifact import DerivedFile

# The one remedy, stated once: every staleness reported here is fixed the same way.
_REMEDY = "run `make regen-docs`"


# ==================================================================================================
#  Findings
# ==================================================================================================
class Stale(abc.ABC):
    """One committed file that no longer agrees with what it should be.

    Two subclasses, because the two ways a file goes stale are reported differently: one can show a
    diff of what changed, the other only knows *that* its inputs moved.
    """

    def __init__(self, artifact: DerivedFile) -> None:
        """Bind the finding to the artifact it was found on."""
        self.artifact = artifact

    @abc.abstractmethod
    def describe(self) -> str:
        """How this staleness reads in the report."""


class StaleContent(Stale):
    """A file whose re-derived content differs from what is committed."""

    def __init__(self, artifact: DerivedFile, committed: str, intended: str) -> None:
        """Record what was found on disk against what the generator now produces."""
        super().__init__(artifact)
        self.committed = committed
        self.intended = intended

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


class StaleInputs(Stale):
    """A rendered file whose inputs changed since it was last built.

    There is no content diff to show — the committed bytes cannot be regenerated here, which is the
    whole reason this artifact is fingerprinted — so the report says what is known instead.
    """

    def __init__(self, artifact: DerivedFile, recorded: str | None) -> None:
        """Record the fingerprint that was on file, if any, against the artifact's current one."""
        super().__init__(artifact)
        self.recorded = recorded

    def describe(self) -> str:
        """A one-line statement of what is known, since no diff is available."""
        if self.recorded is None:
            return f"{self.artifact.path.name}: never recorded -- no fingerprint exists to check it against"
        return f"{self.artifact.path.name}: source content or render settings changed since it was built"


@dataclasses.dataclass(frozen=True)
class RegenerationOutcome:
    """What one regeneration pass produced and what it had to rewrite.

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

    def __init__(self, artifacts: Sequence[DerivedFile], root: Path, manifest_path: Path) -> None:
        """Take ownership of the artifact registry, in the order findings should be reported.

        Args:
            artifacts: Every committed file to keep in step.
            root: Repo root, which the manifest's keys are relative to.
            manifest_path: Where the fingerprint record is committed.
        """
        self._artifacts = artifacts
        self._root = root
        self._manifest_path = manifest_path

    # --------------------------------------------------------------------------
    #  Checking
    # --------------------------------------------------------------------------
    def check(self) -> list[Stale]:
        """Check every artifact by the strongest means available to it.

        An artifact that can be produced here is re-derived and byte-compared. One that cannot
        falls back to comparing its input fingerprint against the manifest. One that is neither
        producible nor fingerprinted is skipped, having nothing checkable on this machine.

        Returns:
            One entry per stale file, in registry order; empty when everything is current.
        """
        manifest = Manifest.load(self._manifest_path)
        stale: list[Stale] = []
        for artifact in self._artifacts:
            if artifact.can_produce_here():
                finding = self._compare_content(artifact)
            else:
                finding = self._compare_fingerprint(artifact, manifest)
            if finding is not None:
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

    def _compare_fingerprint(self, artifact: DerivedFile, manifest: Manifest) -> StaleInputs | None:
        """Compare one unproducible artifact's input fingerprint against the recorded one."""
        fingerprint = artifact.fingerprint()
        if fingerprint is None:
            return None  # unproducible and unfingerprinted: nothing checkable here
        recorded = manifest.recorded(self._manifest_key(artifact))
        if recorded == fingerprint:
            return None
        return StaleInputs(artifact=artifact, recorded=recorded)

    def _manifest_key(self, artifact: DerivedFile) -> str:
        """An artifact's manifest key: its repo-relative path with forward slashes."""
        return artifact.path.relative_to(self._root).as_posix()

    # --------------------------------------------------------------------------
    #  Regenerating
    # --------------------------------------------------------------------------
    def regenerate(self) -> RegenerationOutcome:
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
        return RegenerationOutcome(intended=intended, written=written)

    def record_fingerprints(self) -> None:
        """Record what every fingerprinted artifact was just built from, and commit the manifest.

        Separate from `regenerate` on purpose: the files this describes are built by external
        tooling *after* their sources are written, so recording early would vouch for images that
        a partial run never produced.
        """
        manifest = Manifest.load(self._manifest_path)
        for artifact in self._artifacts:
            if (fingerprint := artifact.fingerprint()) is not None:
                manifest.record(self._manifest_key(artifact), fingerprint)
        manifest.write(self._manifest_path)
