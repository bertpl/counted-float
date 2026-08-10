"""These tests check that no counted operation is missing from the corpus, and that every citation resolves.

`test_golden_counting` proves each row it has is right, which says nothing about the rows
nobody wrote; a new operation or a renamed docs slug surfaces here instead.
"""

from operator import attrgetter

import pytest

from .corpus import ROWS
from .helpers import interpretation_slugs, patched_math_names, reachable_dunders, record_corpus_coverage, rules_anchors

# Each entry names an interpretation no count can observe, with the reason it is excluded from
# the citation check.
_UNCITED_INTERPRETATIONS = {
    # This interpretation fixes how a composite price sums its parts' weights; the corpus
    # asserts counts, not weights.
    "decompositions-sum-latencies",
}


@pytest.mark.parametrize(
    ("all_operations", "reached_operations"),
    [
        (patched_math_names, attrgetter("math_names")),
        (reachable_dunders, attrgetter("dunders")),
    ],
    ids=["math-patches", "dunders"],
)
def test_every_counted_operation_is_pinned_by_a_row(all_operations, reached_operations) -> None:
    """Every patched `math` name and every reachable dunder is exercised by the corpus."""
    # --- act --------------------------
    coverage = record_corpus_coverage()

    # --- assert -----------------------
    assert all_operations() - reached_operations(coverage) == set()


def test_every_citation_resolves_to_a_live_anchor() -> None:
    """Every rule anchor and interpretation slug a row cites exists in the docs pages."""
    # --- arrange ----------------------
    cited = {citation for row in ROWS for citation in row.cites}

    # --- act --------------------------
    unresolved = {
        citation
        for citation in cited
        if citation.removeprefix("rules:") not in rules_anchors()
        and citation.removeprefix("interp:") not in interpretation_slugs()
    }

    # --- assert -----------------------
    assert unresolved == set()


def test_every_cost_model_section_is_cited_by_a_row() -> None:
    """Every rules section and count-observable interpretation is cited by at least one row."""
    # --- arrange ----------------------
    cited = {citation for row in ROWS for citation in row.cites}
    expected = {f"rules:{anchor}" for anchor in rules_anchors()} | {
        f"interp:{slug}" for slug in interpretation_slugs() - _UNCITED_INTERPRETATIONS
    }

    # --- act --------------------------
    uncited = expected - cited

    # --- assert -----------------------
    assert uncited == set()
