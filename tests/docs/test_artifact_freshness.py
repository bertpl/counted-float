"""The freshness driver must pick the right check per artifact, and catch what each one can catch.

Covers the two halves that have no other guard: the fingerprint's sensitivity to every input it
declares, and the driver's dispatch between byte-comparison and the manifest fallback.
"""

import sys
from pathlib import Path

import pytest

# scripts/ is not on the path for a test run, and the machinery lives in a package under it
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
from docs_artifacts import (
    DocsArtifactManager,
    GeneratedFile,
    RenderedFile,
    StaleContent,
    StaleInputs,
)


def _manager(artifacts, tmp_path):
    """A manager over `artifacts`, rooted at `tmp_path` with its manifest alongside."""
    return DocsArtifactManager(artifacts, root=tmp_path, manifest_path=tmp_path / "image_manifest.json")


# ==================================================================================================
#  Fingerprints
# ==================================================================================================
def test_fingerprint_is_stable_across_calls():
    # --- arrange ----------------------------
    artifact = RenderedFile(path=Path("/repo/out.webp"), inputs=lambda: ["capture", "190", "0.6.1"])

    # --- act --------------------------------
    first, second = artifact.fingerprint(), artifact.fingerprint()

    # --- assert -----------------------------
    assert first == second
    assert first.startswith("sha256:")


@pytest.mark.parametrize(
    ("changed", "reason"),
    [
        (["CAPTURE", "190", "0.6.1"], "source content"),
        (["capture", "191", "0.6.1"], "render geometry"),
        (["capture", "190", "0.6.2"], "tool version"),
        (["capture", "190"], "a dropped input"),
    ],
)
def test_fingerprint_changes_when_any_declared_input_changes(changed, reason):
    # --- arrange ----------------------------
    baseline = RenderedFile(path=Path("/repo/out.webp"), inputs=lambda: ["capture", "190", "0.6.1"])
    variant = RenderedFile(path=Path("/repo/out.webp"), inputs=lambda: changed)

    # --- act & assert -----------------------
    assert baseline.fingerprint() != variant.fingerprint(), f"{reason} did not change the fingerprint"


def test_fingerprint_does_not_collide_on_regrouped_inputs():
    """Length-prefixing is what stops `["ab", "c"]` and `["a", "bc"]` hashing alike."""
    # --- arrange ----------------------------
    left = RenderedFile(path=Path("/repo/out.webp"), inputs=lambda: ["ab", "c"])
    right = RenderedFile(path=Path("/repo/out.webp"), inputs=lambda: ["a", "bc"])

    # --- act & assert -----------------------
    assert left.fingerprint() != right.fingerprint()


# ==================================================================================================
#  Manifest
# ==================================================================================================
def test_recorded_manifest_is_sorted_and_keyed_by_relative_path(tmp_path):
    # --- arrange ----------------------------
    artifacts = [
        RenderedFile(path=tmp_path / "images" / "b.webp", inputs=lambda: ["b"]),
        RenderedFile(path=tmp_path / "images" / "a.webp", inputs=lambda: ["a"]),
    ]

    # --- act --------------------------------
    _manager(artifacts, tmp_path).record_fingerprints()
    written = (tmp_path / "image_manifest.json").read_text(encoding="utf-8")

    # --- assert -----------------------------
    assert '"images/a.webp"' in written
    # sorted on write, so a re-record never reshuffles the committed file
    assert written.index('"images/a.webp"') < written.index('"images/b.webp"')


def test_recorded_fingerprints_survive_a_reload(tmp_path):
    # --- arrange ----------------------------
    artifacts = [RenderedFile(path=tmp_path / "out.webp", inputs=lambda: ["inputs"])]
    _manager(artifacts, tmp_path).record_fingerprints()

    # --- act & assert -----------------------
    assert _manager(artifacts, tmp_path).check() == []


# ==================================================================================================
#  Driver dispatch
# ==================================================================================================
def test_producible_artifact_is_byte_compared(tmp_path):
    # --- arrange ----------------------------
    target = tmp_path / "block.md"
    target.write_text("stale", encoding="utf-8")
    artifact = GeneratedFile(path=target, produce=lambda: "fresh")

    # --- act --------------------------------
    stale = _manager([artifact], tmp_path).check()

    # --- assert -----------------------------
    assert len(stale) == 1
    assert isinstance(stale[0], StaleContent)
    assert "fresh" in stale[0].describe()


def test_unproducible_artifact_without_fingerprint_is_skipped(tmp_path):
    """A capture on a platform that cannot produce it has nothing honest to report."""
    # --- arrange ----------------------------
    target = tmp_path / "capture.ansi"
    target.write_text("whatever", encoding="utf-8")
    artifact = GeneratedFile(path=target, produce=lambda: "different", producible_here=False)

    # --- act & assert -----------------------
    assert _manager([artifact], tmp_path).check() == []


def test_rendered_artifact_is_checked_against_the_manifest(tmp_path):
    # --- arrange ----------------------------
    artifact = RenderedFile(path=tmp_path / "out.webp", inputs=lambda: ["inputs"])
    _manager([artifact], tmp_path).record_fingerprints()

    # --- act --------------------------------
    current = _manager([artifact], tmp_path).check()
    drifted = _manager([RenderedFile(path=tmp_path / "out.webp", inputs=lambda: ["other"])], tmp_path).check()

    # --- assert -----------------------------
    assert current == []
    assert len(drifted) == 1
    assert isinstance(drifted[0], StaleInputs)


def test_unrecorded_rendered_artifact_reports_as_never_recorded(tmp_path):
    # --- arrange ----------------------------
    artifact = RenderedFile(path=tmp_path / "out.webp", inputs=lambda: ["inputs"])

    # --- act --------------------------------
    stale = _manager([artifact], tmp_path).check()

    # --- assert -----------------------------
    assert len(stale) == 1
    assert "never recorded" in stale[0].describe()


def test_rendered_artifact_never_asks_for_content(tmp_path):
    """Its bytes are unreproducible here, so requesting them is a bug rather than a fallback."""
    # --- arrange ----------------------------
    artifact = RenderedFile(path=tmp_path / "out.webp", inputs=lambda: ["inputs"])

    # --- act & assert -----------------------
    with pytest.raises(NotImplementedError, match="fingerprint"):
        artifact.intended_content()
