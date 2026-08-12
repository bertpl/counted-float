"""Every patched `math` function must have a delegation reference, and re-capture must rebind it.

The patching module keeps a module-level `original_math_<name>` per patched function, because the
replacements call those names on every delegated call and a module-global read is measurably cheaper
than a dict lookup. That leaves the list of names written in two places -- the declarations and the
patch table -- which is one more than anybody would like, and as few as a type checker allows: the
replacements reference those names directly, so conjuring them at runtime would make them
unresolvable.

Everything downstream of the declarations is derived. Re-capture rebinds them in a loop over the
patch table rather than name by name, so there is no third or fourth copy to drift. The two tests
here cover exactly what remains: that the two lists agree, and that the loop really does move the
references the replacements read -- the one thing no amount of reading the source can confirm,
since rebinding through the module namespace is invisible to static analysis.
"""

import ast
import math
from pathlib import Path

from counted_float._core.counting import math_patching
from counted_float._core.counting.math_patching import _PATCHES, _REFERENCE_PREFIX


# =================================================================================================
#  Helpers
# =================================================================================================
def _declared_reference_names() -> set[str]:
    """The math function names declared as module-level `original_math_<name>` references."""
    tree = ast.parse(Path(math_patching.__file__ or "").read_text(encoding="utf-8"))
    return {
        target.id.removeprefix(_REFERENCE_PREFIX)
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.startswith(_REFERENCE_PREFIX)
    }


# =================================================================================================
#  Tests
# =================================================================================================
def test_the_patch_table_matches_the_declared_references():
    """Every patched function has a reference to delegate through, and vice versa.

    Compared over the functions this interpreter actually has: the references are declared
    unconditionally (with a stand-in where the function is absent), while the patch table registers
    the version-gated ones only when they exist.
    """
    # --- arrange -----------------------------------------
    declared = _declared_reference_names()

    # --- act ---------------------------------------------
    available = {name for name in declared if hasattr(math, name)}

    # --- assert ------------------------------------------
    assert declared, "no original_math_* references found -- was the naming changed?"
    assert available == set(_PATCHES), (
        f"declared but not patched: {sorted(available - set(_PATCHES))}; "
        f"patched with no reference to delegate through: {sorted(set(_PATCHES) - available)}"
    )


def test_recapture_rebinds_every_delegation_reference():
    """The loop must move all of them, not merely run.

    Rebinding happens through this module's own namespace, which no static check can follow -- so
    this points every reference at a sentinel, re-captures, and insists none survived.
    """
    # --- arrange -----------------------------------------
    references = {
        f"{_REFERENCE_PREFIX}{name}": getattr(math_patching, f"{_REFERENCE_PREFIX}{name}") for name in _PATCHES
    }
    sentinel = object()
    for reference in references:
        setattr(math_patching, reference, sentinel)

    # --- act ---------------------------------------------
    try:
        math_patching._capture_originals()
        still_sentinel = [reference for reference in references if getattr(math_patching, reference) is sentinel]
    finally:
        for reference, original in references.items():
            setattr(math_patching, reference, original)

    # --- assert ------------------------------------------
    assert not still_sentinel, f"never rebound by the re-capture: {sorted(still_sentinel)}"
