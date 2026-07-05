"""
Counting replacements for `math` module functions, and the machinery to apply/remove them.

Nothing in this module runs at import time: the `math` module is only patched while at least one
`FlopCountingContext` is active (see `apply_math_patches` / `remove_math_patches`), so merely
importing `counted_float` leaves the process's `math` module untouched.

The `original_math_*` references are (re)captured at patch time, not at import time: another
package may have applied its own `math` patches after we were imported, and we want to delegate
through — and later restore — whatever is current, rather than silently wiping those patches.

The patching contract (mirroring unittest.mock.patch / pytest monkeypatch conventions):
  - at first context entry, we snapshot the current math functions (whatever they are, including
    other packages' patches) and delegate through them while counting;
  - at last context exit, we restore that snapshot, unconditionally — so math.* ends up exactly
    as it was when the first context entered;
  - well-nested (LIFO) third-party patching composes correctly; mis-nested patching (e.g. a patch
    applied inside our context but not removed before we exit) is unsupported: we simply restore
    our snapshot, which discards such patches.
"""

from __future__ import annotations

import math

from ._counted_float import CountedFloat
from ._global_counter import GLOBAL_COUNTER

# -------------------------------------------------------------------------
#  original math module functions
#  (import-time values are only a default; re-captured on every 0->1 patch
#   application by _capture_originals, see module docstring)
# -------------------------------------------------------------------------
original_math_sqrt = math.sqrt
original_math_cbrt = math.cbrt
original_math_log = math.log
original_math_log2 = math.log2
original_math_log10 = math.log10
original_math_exp = math.exp
original_math_exp2 = math.exp2
original_math_pow = math.pow
original_math_sin = math.sin
original_math_cos = math.cos
original_math_tan = math.tan

# sentinel for math_log's optional base argument; the stdlib signature is math.log(x[, base]),
# where omitting base is not the same as passing any real value (and None is rejected)
_NO_BASE = object()


# -------------------------------------------------------------------------
#  counting replacements
# -------------------------------------------------------------------------
def math_sqrt(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_sqrt()
        return CountedFloat(original_math_sqrt(x))
    else:
        return original_math_sqrt(x)


def math_cbrt(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_cbrt()
        return CountedFloat(original_math_cbrt(x))
    else:
        return original_math_cbrt(x)


def math_log(x: float, base=_NO_BASE) -> float | CountedFloat:
    """
    Patched math.log: stdlib contract (optional base), with flop classification for the base
    following the same constant-detection heuristic as CountedFloat.__pow__ / __rpow__
    (int operand = hardcoded constant in the source):
      - base omitted      -> LOG
      - base int 2 / 10   -> LOG2 / LOG10 (a compiled port calls log2/log10 directly)
      - base other int    -> LOG + MUL (a port computes log(x) * C, with C = 1/log(base) folded
                             at compile time)
      - base float        -> a port computes log(x)/log(base): LOG per CountedFloat operand + DIV
    As everywhere in the counting model, only operations touching CountedFloat values are counted:
    any runtime input to the counted algorithm should itself be a CountedFloat; whatever remains a
    plain float is by definition not part of the core algorithm and/or precomputable.
    """
    if base is _NO_BASE:
        if isinstance(x, CountedFloat):
            GLOBAL_COUNTER.incr_log()
            return CountedFloat(original_math_log(x))
        else:
            return original_math_log(x)
    else:
        # computed first: raises per stdlib contract before anything is counted
        result = original_math_log(x, base)
        if isinstance(base, int) and base == 2:
            if isinstance(x, CountedFloat):
                GLOBAL_COUNTER.incr_log2()
        elif isinstance(base, int) and base == 10:
            if isinstance(x, CountedFloat):
                GLOBAL_COUNTER.incr_log10()
        elif isinstance(base, int):
            if isinstance(x, CountedFloat):
                GLOBAL_COUNTER.incr_log()
                GLOBAL_COUNTER.incr_mul()
        else:
            if isinstance(x, CountedFloat):
                GLOBAL_COUNTER.incr_log()
            if isinstance(base, CountedFloat):
                GLOBAL_COUNTER.incr_log()
            if isinstance(x, CountedFloat) or isinstance(base, CountedFloat):
                GLOBAL_COUNTER.incr_div()
        if isinstance(x, CountedFloat) or isinstance(base, CountedFloat):
            return CountedFloat(result)
        else:
            return result


def math_log2(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_log2()
        return CountedFloat(original_math_log2(x))
    else:
        return original_math_log2(x)


def math_log10(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_log10()
        return CountedFloat(original_math_log10(x))
    else:
        return original_math_log10(x)


def math_exp(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_exp()
        return CountedFloat(original_math_exp(x))
    else:
        return original_math_exp(x)


def math_exp2(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_exp2()
        return CountedFloat(original_math_exp2(x))
    else:
        return original_math_exp2(x)


def math_pow(x: float, y: float) -> float | CountedFloat:
    """
    Patched math.pow: stdlib contract (always-float result, ValueError on domain errors), with
    flop classification identical to the x**y form — including the constant-detection heuristic
    documented on CountedFloat.__pow__ / __rpow__ (int operand = hardcoded constant).
    """
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        # computed first: math.pow raises ValueError on domain errors (e.g. negative base with
        # fractional exponent) and then nothing should be counted
        result = original_math_pow(x, y)
        if isinstance(x, CountedFloat):
            if isinstance(y, int) and y == 2:
                GLOBAL_COUNTER.incr_mul()  # x^2 = x*x
            else:
                if isinstance(y, int):
                    GLOBAL_COUNTER.incr_i2f()
                GLOBAL_COUNTER.incr_pow()
        else:
            if isinstance(x, int) and x == 2:
                GLOBAL_COUNTER.incr_exp2()
            elif isinstance(x, int) and x == 10:
                GLOBAL_COUNTER.incr_exp10()
            else:
                if isinstance(x, int):
                    GLOBAL_COUNTER.incr_i2f()
                GLOBAL_COUNTER.incr_pow()
        return CountedFloat(result)
    else:
        return original_math_pow(x, y)


def math_sin(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_sin()
        return CountedFloat(original_math_sin(x))
    else:
        return original_math_sin(x)


def math_cos(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_cos()
        return CountedFloat(original_math_cos(x))
    else:
        return original_math_cos(x)


def math_tan(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_tan()
        return CountedFloat(original_math_tan(x))
    else:
        return original_math_tan(x)


# -------------------------------------------------------------------------
#  applying / removing the patches
# -------------------------------------------------------------------------
_PATCHES: dict[str, object] = {
    "sqrt": math_sqrt,
    "cbrt": math_cbrt,
    "log": math_log,
    "log2": math_log2,
    "log10": math_log10,
    "exp": math_exp,
    "exp2": math_exp2,
    "pow": math_pow,
    "sin": math_sin,
    "cos": math_cos,
    "tan": math_tan,
}
# the math functions saved at patch time, to be restored at unpatch time
_saved_originals: dict[str, object] = {}

# number of currently active FlopCountingContext instances; patches are applied on the 0->1
# transition and removed on the 1->0 transition, so nested contexts behave correctly
# (NOT thread-safe, like the rest of the counting machinery)
_active_context_count = 0


def _capture_originals():
    """Snapshot the current math functions, so the replacements delegate through (and unpatching
    restores) whatever is current — possibly another package's patches, not the stdlib originals."""
    global original_math_sqrt, original_math_cbrt, original_math_log, original_math_log2
    global original_math_log10, original_math_exp, original_math_exp2, original_math_pow
    global original_math_sin, original_math_cos, original_math_tan

    original_math_sqrt = math.sqrt
    original_math_cbrt = math.cbrt
    original_math_log = math.log
    original_math_log2 = math.log2
    original_math_log10 = math.log10
    original_math_exp = math.exp
    original_math_exp2 = math.exp2
    original_math_pow = math.pow
    original_math_sin = math.sin
    original_math_cos = math.cos
    original_math_tan = math.tan

    _saved_originals.clear()
    for name in _PATCHES:
        _saved_originals[name] = getattr(math, name)


def apply_math_patches():
    """Apply the counting replacements to the math module (refcounted; see module docstring)."""
    global _active_context_count
    _active_context_count += 1
    if _active_context_count == 1:
        _capture_originals()
        for name, replacement in _PATCHES.items():
            setattr(math, name, replacement)


def remove_math_patches():
    """Undo apply_math_patches; the math module is restored once the last context exits."""
    global _active_context_count
    _active_context_count = max(0, _active_context_count - 1)
    if _active_context_count == 0:
        # restore the snapshot unconditionally, assuming LIFO patching discipline of any other
        # patching packages (see module docstring for the exact contract)
        for name, saved in _saved_originals.items():
            setattr(math, name, saved)
