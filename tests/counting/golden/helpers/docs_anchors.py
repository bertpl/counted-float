"""Extract the anchors the cost-model pages define, so a row's citations can be checked against them.

The interpretations page defines no explicit anchors: each entry's level-2 heading text is
itself the frozen slug.
"""

import re
from pathlib import Path

_RULES_PAGE_NAME = "cost_model_rules.md"
_INTERPRETATIONS_PAGE_NAME = "cost_model_interpretations.md"


def _docs_dir() -> Path:
    """Locate the docs directory by walking up from this file.

    The mutation runner copies only the package and the tests into its sandbox, so the docs
    sit one level further up there than in the repo. Searching upward finds them under both
    layouts, where a fixed number of parents finds them under only one.
    """
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "docs" / _RULES_PAGE_NAME).is_file():
            return ancestor / "docs"
    raise FileNotFoundError(f"no ancestor of {__file__} holds docs/{_RULES_PAGE_NAME}")


_RULES_PAGE = _docs_dir() / _RULES_PAGE_NAME
_INTERPRETATIONS_PAGE = _docs_dir() / _INTERPRETATIONS_PAGE_NAME

_EXPLICIT_ANCHOR = re.compile(r"\{ #([a-z0-9-]+) \}")
_ENTRY_HEADING = re.compile(r"^## ([a-z0-9-]+)$", re.MULTILINE)


def rules_anchors() -> set[str]:
    """Return the section anchors defined by the cost-model rules page."""
    return set(_EXPLICIT_ANCHOR.findall(_RULES_PAGE.read_text(encoding="utf-8")))


def interpretation_slugs() -> set[str]:
    """Return the entry slugs defined by the cost-model interpretations page."""
    return set(_ENTRY_HEADING.findall(_INTERPRETATIONS_PAGE.read_text(encoding="utf-8")))
