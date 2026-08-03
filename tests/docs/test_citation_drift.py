"""CITATION.cff must cite the latest released version, exactly as the changelog records it.

Both files are stamped by the release flow in the same commit; this pins that they cannot drift
apart between releases (e.g. through a hand edit to either file).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CITATION = REPO_ROOT / "CITATION.cff"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def _citation_field(name: str) -> str:
    """The value of a top-level `name:` field in CITATION.cff."""
    match = re.search(rf"^{name}: (.+)$", CITATION.read_text(), re.MULTILINE)
    assert match, f"CITATION.cff has no '{name}:' field"
    return match.group(1).strip()


def _latest_changelog_release() -> tuple[str, str]:
    """The (version, date) of the newest dated version section in CHANGELOG.md."""
    match = re.search(r"^## (\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)$", CHANGELOG.read_text(), re.MULTILINE)
    assert match, "CHANGELOG.md has no dated version section"
    return match.group(1), match.group(2)


def test_citation_cites_the_latest_released_version():
    # --- arrange / act -------------------------
    version, released = _latest_changelog_release()

    # --- assert --------------------------------
    assert _citation_field("version") == version
    assert _citation_field("date-released") == released
