# The plain-text layout of the tree is byte-checked by the docs-drift test (via the show-data slice),
# so it is not re-pinned here. These tests cover what the drift test does NOT: the integer-weight
# format (every drift block renders float weights) and the ANSI styling (the drift test strips color).
from counted_float._core.counting.builtin_data._tree_view import FlopWeightsTreeView
from counted_float._core.models import FlopType, FlopWeights


def test_tree_view_renders_integer_weights_without_decimals(capsys, monkeypatch):
    # nearest_int weights take the integer format (str(w)) rather than the 2-decimal float format
    # --- arrange -----------------------------------------
    monkeypatch.setenv("COLUMNS", "80")
    fw_int = FlopWeights(weights={FlopType.ADD: 3.0, FlopType.MUL: 7.0}).round("nearest_int")
    tree = FlopWeightsTreeView.from_nested_dict("r", {"x": fw_int})

    # --- act ---------------------------------------------
    tree.show()
    leaf_line = capsys.readouterr().out.splitlines()[2]

    # --- assert ------------------------------------------
    assert leaf_line.startswith(" └─x")
    assert "         3         7 " in leaf_line  # bare ints, right-justified in width-10 columns
    assert "3.00" not in leaf_line  # not the float format


def test_tree_view_styles_non_leaf_rows_and_leaves_plain(capsys, monkeypatch):
    # FORCE_COLOR makes rich emit ANSI even into the captured (non-tty) buffer, so the styling --
    # a bold legend, colored non-leaf rows spliced after the 3*indent connector, and plain leaf rows
    # (no styling, no auto-highlight) -- becomes observable.
    # --- arrange -----------------------------------------
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("FORCE_COLOR", "1")
    fw_a = FlopWeights(weights={FlopType.ADD: 1.0})
    fw_b = FlopWeights(weights={FlopType.ADD: 3.0})
    tree = FlopWeightsTreeView.from_nested_dict("root", {"leaf_a": fw_a, "branch": {"leaf_b": fw_b}})

    # --- act ---------------------------------------------
    tree.show()
    lines = capsys.readouterr().out.splitlines()

    # --- assert ------------------------------------------
    esc = "\x1b["
    assert lines[0].startswith(esc + "1m")  # legend is bold
    assert lines[1].startswith(esc)  # root (non-leaf, indent 0) is styled from column 0
    assert lines[2].startswith(" ├─" + esc)  # branch (non-leaf, indent 1) is styled after the 3-char connector
    assert esc not in lines[3]  # leaf_b is a leaf -> no styling, no auto-highlight
    assert esc not in lines[4]  # leaf_a is a leaf -> plain
