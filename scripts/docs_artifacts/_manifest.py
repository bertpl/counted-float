"""The committed record of what each non-reproducible artifact was last built from.

A file whose generator cannot run in CI has nothing to compare against there — so instead of its
bytes, we record a hash of everything it is a function of, and check *that*. The record is plain
JSON keyed by repo-relative path: no image library, no metadata reader, nothing to parse but the
manifest itself.

Storing the hash inside the image was considered and dropped: a WebP needs a binary metadata reader
in CI and the hash would have to survive `magick`'s `-strip`. A sidecar gives the same guarantee,
works the same way for any format, and stays readable in a diff.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class Manifest:
    """Recorded input fingerprints, keyed by the artifact's repo-relative path."""

    def __init__(self, entries: dict[str, str]) -> None:
        self._entries = entries

    # --------------------------------------------------------------------------
    #  Construction
    # --------------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> Manifest:
        """Read a manifest, treating an absent file as an empty one.

        An absent manifest makes every fingerprinted artifact report as stale, which is the right
        answer: nothing has been recorded, so nothing can be vouched for.
        """
        if not path.exists():
            return cls({})
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def write(self, path: Path) -> None:
        """Write the manifest sorted and newline-terminated, so its diffs stay reviewable."""
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(dict(sorted(self._entries.items())), indent=2) + "\n"
        path.write_text(serialized, encoding="utf-8", newline="\n")

    # --------------------------------------------------------------------------
    #  Access
    # --------------------------------------------------------------------------
    def recorded(self, key: str) -> str | None:
        """The fingerprint recorded for `key`, or None when it has never been recorded."""
        return self._entries.get(key)

    def record(self, key: str, fingerprint: str) -> None:
        """Set the fingerprint for `key`, replacing any previous value."""
        self._entries[key] = fingerprint
