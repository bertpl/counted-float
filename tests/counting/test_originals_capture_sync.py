"""The same list of `math` function names is written in four places; they must agree.

The patching module keeps a module-level `original_math_<name>` reference per patched function, and
re-points every one of them each time patching starts, so the replacements delegate through whatever
is current -- possibly another package's patch rather than the stdlib original. That arrangement
spells the same list of names four times: the import-time references, the `global` declarations in
the re-capture step, the re-capture assignments themselves, and the patch table.

Two ways to get it wrong, both invisible in normal operation:

* a name in the patch table with no reference to delegate through, or one that is never re-captured,
  leaves a stale reference -- correct until another package patches `math` first;
* a name assigned in the re-capture step but missing from its `global` declaration is not an error
  at all. Python simply makes it a function-local, so the assignment writes nothing anybody reads
  and that function keeps its import-time reference forever.

The second is the reason this test parses the source rather than only comparing the tables: the
other three lists agree perfectly while it is wrong.

The duplication is deliberate and stays. Reading a module-level name is what keeps delegation off a
dict lookup on the hot path, so the guard goes on the invariant rather than on collapsing the lists.
"""

import ast
import math
from pathlib import Path

from counted_float._core.counting import _math_patching
from counted_float._core.counting._math_patching import _PATCHES

_REFERENCE_PREFIX = "original_math_"
_CAPTURE_FUNCTION = "_capture_originals"


# =================================================================================================
#  Helpers
# =================================================================================================
def _module_tree() -> ast.Module:
    """Parse the patching module's own source."""
    return ast.parse(Path(_math_patching.__file__ or "").read_text(encoding="utf-8"))


def _referenced_names(nodes: list[ast.stmt]) -> set[str]:
    """The math function names assigned as `original_math_<name>` directly among `nodes`."""
    return {
        target.id.removeprefix(_REFERENCE_PREFIX)
        for node in nodes
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.startswith(_REFERENCE_PREFIX)
    }


def _capture_function(tree: ast.Module) -> ast.FunctionDef:
    """The re-capture function's node."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == _CAPTURE_FUNCTION:
            return node
    raise AssertionError(f"{_CAPTURE_FUNCTION} not found -- was it renamed?")


def _declared_global(function: ast.FunctionDef) -> set[str]:
    """The math function names declared global inside `function`."""
    return {
        name.removeprefix(_REFERENCE_PREFIX)
        for node in ast.walk(function)
        if isinstance(node, ast.Global)
        for name in node.names
        if name.startswith(_REFERENCE_PREFIX)
    }


# =================================================================================================
#  Tests
# =================================================================================================
def test_the_import_time_references_match_the_recaptured_ones():
    # --- arrange -----------------------------------------
    tree = _module_tree()

    # --- act ---------------------------------------------
    at_import = _referenced_names(tree.body)
    recaptured = _referenced_names(_capture_function(tree).body)

    # --- assert ------------------------------------------
    assert at_import, "no original_math_* references found -- was the naming changed?"
    assert at_import == recaptured, (
        f"never re-captured: {sorted(at_import - recaptured)}; "
        f"re-captured without an import-time reference: {sorted(recaptured - at_import)}"
    )


def test_every_recaptured_reference_is_declared_global():
    """Otherwise the assignment silently writes a function-local and re-capture does nothing."""
    # --- arrange -----------------------------------------
    capture = _capture_function(_module_tree())

    # --- act ---------------------------------------------
    recaptured = _referenced_names(capture.body)
    declared = _declared_global(capture)

    # --- assert ------------------------------------------
    assert recaptured == declared, (
        f"assigned but not declared global (the re-capture is a no-op for these): "
        f"{sorted(recaptured - declared)}; "
        f"declared global but never assigned: {sorted(declared - recaptured)}"
    )


def test_the_patch_table_matches_the_references():
    """Every patched function has a reference to delegate through, and vice versa.

    Compared over the functions this interpreter actually has: the references are declared
    unconditionally (with a stand-in where the function is absent), while the patch table registers
    the version-gated ones only when they exist.
    """
    # --- arrange -----------------------------------------
    at_import = _referenced_names(_module_tree().body)

    # --- act ---------------------------------------------
    available = {name for name in at_import if hasattr(math, name)}

    # --- assert ------------------------------------------
    assert available == set(_PATCHES), (
        f"referenced but not patched: {sorted(available - set(_PATCHES))}; "
        f"patched with no reference to delegate through: {sorted(set(_PATCHES) - available)}"
    )


def test_the_recapture_actually_rebinds_the_module_level_reference():
    """The behavioral counterpart: re-capturing must move the reference the replacements read.

    The AST tests above cannot see a reference that is rebound somewhere other than where they
    looked; this one just does it and checks.
    """
    # --- arrange -----------------------------------------
    name = next(iter(_PATCHES))
    reference = f"{_REFERENCE_PREFIX}{name}"
    original = getattr(_math_patching, reference)
    sentinel = object()
    setattr(_math_patching, reference, sentinel)

    # --- act ---------------------------------------------
    try:
        _math_patching._capture_originals()
        recaptured = getattr(_math_patching, reference)
    finally:
        setattr(_math_patching, reference, original)

    # --- assert ------------------------------------------
    assert recaptured is not sentinel, f"{reference} was not rebound by the re-capture"
