"""Every public callable of `math` must be accounted for by one of the classification tables.

CPython keeps adding float functions to `math` - `cbrt` and `exp2`, then `sumprod`, then `fma` -
and each addition that nobody classifies becomes a silently uncounted hole: contagion stops there,
the total comes out wrong, and nothing anywhere says so.  Pinning the surface turns that from a
defect someone eventually notices into a test failure at the moment the interpreter changes.

The three tables are exhaustive and disjoint by construction:

* ``_PATCHES``           - replaced while counting, so the call registers its flops;
* ``_UNCOUNTED_MATH``    - deliberately uninstrumented, and reported at WARNING verbosity;
* ``_MATH_NOT_PATCHED``  - needs no replacement at all, with the reason per entry.

Version-conditional functions need no handling here: the tables register them conditionally
themselves, so both directions of the comparison hold on every supported Python.
"""

import math

from counted_float._core.counting._math_patching import _MATH_NOT_PATCHED, _PATCHES, _UNCOUNTED_MATH

_TABLES = {
    "_PATCHES (instrument it, and give it a FlopType)": set(_PATCHES),
    "_UNCOUNTED_MATH (leave it uncounted, and report it at WARNING verbosity)": set(_UNCOUNTED_MATH),
    "_MATH_NOT_PATCHED (needs no replacement - say why)": set(_MATH_NOT_PATCHED),
}


# =================================================================================================
#  Helpers
# =================================================================================================
def _public_math_callables() -> set[str]:
    """Every callable `math` exposes under a public name, on the running interpreter."""
    return {name for name in dir(math) if not name.startswith("_") and callable(getattr(math, name))}


# =================================================================================================
#  Tests
# =================================================================================================
def test_every_public_math_callable_is_classified():
    # --- arrange / act -------------------------
    unclassified = _public_math_callables() - set().union(*_TABLES.values())

    # --- assert --------------------------------
    assert not unclassified, (
        f"unclassified `math` callable(s): {sorted(unclassified)}.\n"
        "Each one belongs in exactly one of:\n" + "\n".join(f"  - {table}" for table in _TABLES)
    )


def test_no_table_classifies_a_function_math_does_not_have():
    # --- arrange / act -------------------------
    surface = _public_math_callables()
    phantom = {name: table for table, names in _TABLES.items() for name in names - surface}

    # --- assert --------------------------------
    assert not phantom, f"classified but absent from `math` on this interpreter: {phantom}"


def test_the_tables_do_not_overlap():
    # --- arrange / act -------------------------
    overlapping = {
        name: sorted(table for table, names in _TABLES.items() if name in names)
        for name in set().union(*_TABLES.values())
        if sum(name in names for names in _TABLES.values()) > 1
    }

    # --- assert --------------------------------
    assert not overlapping, f"`math` callable(s) classified more than once: {overlapping}"


def test_every_unpatched_entry_carries_a_reason():
    # --- arrange / act -------------------------
    reasonless = [name for name, reason in _MATH_NOT_PATCHED.items() if not reason.strip()]

    # --- assert --------------------------------
    assert not reasonless, f"entries with no stated reason for going unpatched: {reasonless}"
