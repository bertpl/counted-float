"""The marked-block rewriting engine must fail loudly on any malformed marker structure."""

import sys
from pathlib import Path

import pytest

# scripts/ is not on the path for a test run, and the engine lives in a package under it
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
from docs_artifacts import rewrite_marked_blocks

_FILE = Path("some_doc.md")


def test_marked_block_is_replaced_and_surroundings_untouched():
    # --- arrange -----------------------------------------
    text = "before\n<!-- BEGIN generated: a -->\nstale\n<!-- END generated: a -->\nafter\n"

    # --- act ---------------------------------------------
    result = rewrite_marked_blocks(text, _FILE, {"a": "fresh"})

    # --- assert ------------------------------------------
    assert result == "before\n<!-- BEGIN generated: a -->\nfresh\n<!-- END generated: a -->\nafter\n"


@pytest.mark.parametrize(
    ("text", "error_match"),
    [
        ("<!-- BEGIN generated: a -->\n<!-- BEGIN generated: b -->\n", "nested BEGIN"),
        ("<!-- END generated: a -->\n", "without a BEGIN"),
        ("<!-- BEGIN generated: a -->\n<!-- END generated: b -->\n", "closes BEGIN"),
        ("<!-- BEGIN generated: a -->\n", "never closed"),
        ("<!-- BEGIN generated: x -->\n<!-- END generated: x -->\n", "no registered generator"),
        ("no markers here\n", "expected markers not found"),
    ],
)
def test_malformed_markers_fail_loudly(text, error_match):
    # --- act & assert ------------------------------------
    with pytest.raises(ValueError, match=error_match):
        rewrite_marked_blocks(text, _FILE, {"a": "fresh"})


def test_duplicate_marker_fails_loudly():
    # --- arrange -----------------------------------------
    text = (
        "<!-- BEGIN generated: a -->\n<!-- END generated: a -->\n"
        "<!-- BEGIN generated: a -->\n<!-- END generated: a -->\n"
    )

    # --- act & assert ------------------------------------
    with pytest.raises(ValueError, match="duplicate marker"):
        rewrite_marked_blocks(text, _FILE, {"a": "fresh"})
