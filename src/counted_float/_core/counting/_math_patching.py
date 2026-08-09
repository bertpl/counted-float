"""Replacements for `math` module functions, and the machinery to apply/remove them.

There are two independently applied sets, each with its own lifetime:
  - the **counting** replacements (`_PATCHES`), installed while at least one `FlopCountingContext`
    is open — they count what they delegate to;
  - the **reporting** replacements (`_UNCOUNTED_PATCHES`), installed while at least one thread is
    reporting — they count nothing and exist only to surface the functions that cannot be counted
    (see `_UNCOUNTED_MATH`). Their lifetime is strictly nested inside the counting set's, since a
    reporting thread necessarily has a context open, and a run at the default verbosity never
    installs them at all.

Nothing in this module runs at import time: the `math` module is only patched while at least one
`FlopCountingContext` is active (see `apply_math_patches` / `remove_math_patches`), so merely
importing `counted_float` leaves the process's `math` module untouched.

The `original_math_*` references are (re)captured at patch time, not at import time: another
package may have applied its own `math` patches after we were imported, and we want to delegate
through — and later restore — whatever is current, rather than silently wiping those patches.

**Map of the name-keyed tables.** Four are maintained by hand, and they are not four copies of one
list: `_PATCHES`, `_UNCOUNTED_MATH` and `_MATH_NOT_PATCHED` are the *classification*, and every
public `math` function belongs to exactly one of them. `original_math_*` is the one place a name is
genuinely written twice — unavoidably, since the replacements call those names directly and a type
checker has to be able to resolve them. Everything below those four is derived or filled at runtime.

  | table                  | holds                          | written        | read              |
  |------------------------|--------------------------------|----------------|-------------------|
  | `_PATCHES`             | name -> counting replacement   | by hand        | capture/apply/restore |
  | `original_math_*`      | name -> delegation target      | by hand¹       | every delegated call |
  | `_UNCOUNTED_MATH`      | name -> why it goes uncounted  | by hand        | builds the next one |
  | `_MATH_NOT_PATCHED`    | name -> why it needs no patch  | by hand        | the surface test, docs |
  | `_UNCOUNTED_PATCHES`   | name -> reporting replacement  | derived        | apply/restore     |
  | `_saved_originals`     | name -> function to restore    | at capture     | restore           |
  | `_uncounted_originals` | name -> function to delegate to| at apply       | reporting replacements |

  ¹ only the *names* are; their values are always overwritten by `_capture_originals`.

  That the three classification tables really do partition the surface — exhaustively and without
  overlap — is enforced by a test, so a function CPython adds later cannot slip through
  unclassified.

**Lifecycle**, in order: import (declare references and tables) -> first context entry (capture the
current `math`, install `_PATCHES`) -> first reporting thread (install `_UNCOUNTED_PATCHES`) -> last
reporting thread leaves (restore those) -> last context exit (restore the capture).

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
import threading
from math import copysign as _copysign  # the raw builtin: math.copysign is patched inside contexts
from typing import TYPE_CHECKING, Never

from ._counted_float import CountedFloat, count_pow_with_constant_base, count_pow_with_constant_exponent
from ._thread_counter import _TLS, _create_thread_state, thread_is_reporting
from .verbosity import warn_uncounted_call

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from ._thread_counter import CountsTarget


def _unavailable_stand_in(name: str, minimum_version: str) -> Callable[..., Never]:
    """Build the stand-in for a `math` function the running interpreter predates.

    None of these is ever called: a counting replacement is registered only where its `math`
    function exists (see _PATCHES). They exist so every `original_math_*` reference is callable
    on every supported interpreter rather than `None`, which would make the patches' own call
    sites unsound. Returning `Never` is what lets one builder serve them all: the delegating
    patches declare `float` and `bool` return types, and a call that cannot return satisfies
    either.

    Args:
        name: Name of the `math` function that is missing here.
        minimum_version: First Python version providing it, for the raised message.

    Returns:
        A replacement that raises `NotImplementedError` whatever it is passed.
    """

    def stand_in(*args: object, **kwargs: object) -> Never:
        raise NotImplementedError(f"math.{name} requires Python {minimum_version} or newer")

    return stand_in


_math_sumprod_unavailable = _unavailable_stand_in("sumprod", "3.12")
_math_fma_unavailable = _unavailable_stand_in("fma", "3.13")
_math_fmax_unavailable = _unavailable_stand_in("fmax", "3.15")
_math_fmin_unavailable = _unavailable_stand_in("fmin", "3.15")
_math_isnormal_unavailable = _unavailable_stand_in("isnormal", "3.15")
_math_issubnormal_unavailable = _unavailable_stand_in("issubnormal", "3.15")
_math_signbit_unavailable = _unavailable_stand_in("signbit", "3.15")


# -------------------------------------------------------------------------
#  original math module functions
#  (import-time values are only a default; re-captured on every 0->1 patch
#   application by _capture_originals, see module docstring)
#
#  Written out one per line rather than generated, for one reason: the
#  replacements below call these names directly, and a name conjured at
#  runtime is a name the type checker cannot resolve. Their *values* are
#  never maintained here -- _capture_originals rebinds every one of them --
#  so what these lines really declare is which functions exist to delegate
#  to, which a test holds against the patch table.
# -------------------------------------------------------------------------
_REFERENCE_PREFIX = "original_math_"

original_math_sqrt = math.sqrt
original_math_cbrt = math.cbrt
original_math_log = math.log
original_math_log2 = math.log2
original_math_log10 = math.log10
original_math_exp = math.exp
original_math_exp2 = math.exp2
original_math_pow = math.pow
original_math_fma = getattr(math, "fma", _math_fma_unavailable)
original_math_sin = math.sin
original_math_cos = math.cos
original_math_tan = math.tan
original_math_asin = math.asin
original_math_acos = math.acos
original_math_atan = math.atan
original_math_atan2 = math.atan2
original_math_hypot = math.hypot
original_math_expm1 = math.expm1
original_math_log1p = math.log1p
original_math_fmod = math.fmod
original_math_fabs = math.fabs
original_math_sinh = math.sinh
original_math_cosh = math.cosh
original_math_tanh = math.tanh
original_math_asinh = math.asinh
original_math_acosh = math.acosh
original_math_atanh = math.atanh
original_math_degrees = math.degrees
original_math_radians = math.radians
original_math_dist = math.dist
original_math_prod = math.prod
original_math_fsum = math.fsum
original_math_copysign = math.copysign
original_math_isnan = math.isnan
original_math_isinf = math.isinf
original_math_isfinite = math.isfinite
original_math_isclose = math.isclose
original_math_gamma = math.gamma
original_math_lgamma = math.lgamma
original_math_erf = math.erf
original_math_erfc = math.erfc
original_math_remainder = math.remainder
original_math_sumprod = getattr(math, "sumprod", _math_sumprod_unavailable)
original_math_fmax = getattr(math, "fmax", _math_fmax_unavailable)
original_math_fmin = getattr(math, "fmin", _math_fmin_unavailable)
original_math_isnormal = getattr(math, "isnormal", _math_isnormal_unavailable)
original_math_issubnormal = getattr(math, "issubnormal", _math_issubnormal_unavailable)
original_math_signbit = getattr(math, "signbit", _math_signbit_unavailable)

# sentinel for math_log's optional base argument; the stdlib signature is math.log(x[, base]),
# where omitting base is not the same as passing any real value (and None is rejected)
_NO_BASE = object()


# -------------------------------------------------------------------------
#  counting replacements
# -------------------------------------------------------------------------
def math_sqrt(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_sqrt(x)  # compute first: domain error (x < 0) raises before counting
        try:
            _TLS.flop_counts.SQRT += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().SQRT += 1
        return float.__new__(CountedFloat, result)
    return original_math_sqrt(x)


def math_cbrt(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_cbrt(x)
        try:
            _TLS.flop_counts.CBRT += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().CBRT += 1
        return float.__new__(CountedFloat, result)
    return original_math_cbrt(x)


def math_log(  # noqa: C901 -- branches mirror the per-log-variant counting rules
    x: float,
    base: float = _NO_BASE,  # ty: ignore[invalid-parameter-default] -- sentinel mirrors math.log's omittable base
) -> float | CountedFloat:
    """Patch math.log: stdlib contract (optional base), with flop classification per log variant.

    Flop classification for the base treats any constant (non-CountedFloat) base as a
    compile-time constant, folded by value (as everywhere in the counting model), mirroring
    CountedFloat.__pow__ / __rpow__:
      - base omitted           -> LOG
      - constant base 2 / 10   -> LOG2 / LOG10 (a compiled port calls log2/log10 directly)
      - other constant base    -> LOG + MUL (a port computes log(x) * C, with C = 1/log(base)
                                  folded at compile time); C is itself a constant, so the
                                  identity folds apply to the multiply: C = 1.0 (base e on a
                                  libm that rounds log(e) to exactly 1.0) drops it, C = -1.0
                                  makes it a bare sign flip (MINUS)
      - CountedFloat base      -> genuinely runtime: a port computes log(x)/log(base), so
                                  LOG per CountedFloat operand + DIV
    As everywhere in the counting model, only operations touching CountedFloat values are counted:
    any runtime input to the counted algorithm should itself be a CountedFloat; whatever remains a
    plain float is by definition not part of the core algorithm and/or precomputable.
    """
    if base is _NO_BASE:
        if isinstance(x, CountedFloat):
            result = original_math_log(x)  # compute first: domain error (x <= 0) raises before counting
            try:
                _TLS.flop_counts.LOG += 1
            except AttributeError:  # first counted op on this thread
                _create_thread_state().LOG += 1
            return float.__new__(CountedFloat, result)
        return original_math_log(x)
    # computed first: raises per stdlib contract before anything is counted
    result = original_math_log(x, base)
    if not (isinstance(x, CountedFloat) or isinstance(base, CountedFloat)):
        # settle the uncountable case before touching the counter: fetching it on a thread that
        # counted nothing would allocate that thread's state for no reason
        return result
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    if isinstance(base, CountedFloat):
        cnt.note("runtime base -> log(x)/log(base)")
        if isinstance(x, CountedFloat):
            cnt.LOG += 1
        cnt.LOG += 1
        cnt.DIV += 1
    elif float(base) == 2.0:
        if isinstance(x, CountedFloat):
            cnt.note("const base 2 -> log2")
            cnt.LOG2 += 1
    elif float(base) == 10.0:
        if isinstance(x, CountedFloat):
            cnt.note("const base 10 -> log10")
            cnt.LOG10 += 1
    else:
        if isinstance(x, CountedFloat):
            # the port precomputes C = 1/log(base) and multiplies by it; a C of exactly +/-1.0
            # identity-folds like any constant multiplier. Computing log(base) here mirrors that
            # compile-time evaluation -- as for every fold, the observed value decides
            log_of_base = original_math_log(float(base))
            if log_of_base == 1.0:
                cnt.note("const base -> log(x); the 1/log(base) multiplier is 1.0 and folds away")
                cnt.LOG += 1
            elif log_of_base == -1.0:
                cnt.note("const base -> log(x) * -1.0 -> sign flip")
                cnt.LOG += 1
                cnt.MINUS += 1
            else:
                cnt.note("const base -> log(x) * 1/log(base)")
                cnt.LOG += 1
                cnt.MUL += 1
    # the guard above already established that at least one operand is counted
    return float.__new__(CountedFloat, result)


def math_log2(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_log2(x)  # compute first: domain error (x <= 0) raises before counting
        try:
            _TLS.flop_counts.LOG2 += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().LOG2 += 1
        return float.__new__(CountedFloat, result)
    return original_math_log2(x)


def math_log10(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_log10(x)  # compute first: domain error (x <= 0) raises before counting
        try:
            _TLS.flop_counts.LOG10 += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().LOG10 += 1
        return float.__new__(CountedFloat, result)
    return original_math_log10(x)


def math_exp(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_exp(x)  # compute first: exp overflows (OverflowError) before counting
        try:
            _TLS.flop_counts.EXP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().EXP += 1
        return float.__new__(CountedFloat, result)
    return original_math_exp(x)


def math_exp2(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_exp2(x)  # compute first: exp2 overflows (OverflowError) before counting
        try:
            _TLS.flop_counts.EXP2 += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().EXP2 += 1
        return float.__new__(CountedFloat, result)
    return original_math_exp2(x)


def math_pow(x: float, y: float) -> float | CountedFloat:
    """Patch math.pow: stdlib contract (always-float result, ValueError on domain errors).

    Flop classification is identical to the x**y form (strength reduction for hardcoded int
    exponents/bases; int operands are compile-time constants and add no I2F) — see
    CountedFloat.__pow__ / __rpow__.
    """
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        # computed first: math.pow raises ValueError on domain errors (e.g. negative base with
        # fractional exponent) and then nothing should be counted
        result = original_math_pow(x, y)
        if isinstance(x, CountedFloat) and isinstance(y, CountedFloat):
            try:
                _TLS.flop_counts.POW += 1  # genuinely runtime base and exponent
            except AttributeError:  # first counted op on this thread
                _create_thread_state().POW += 1
        elif isinstance(x, CountedFloat):
            if float(y) == 0.0:
                return result  # pow(x, 0) is 1.0 for every x: the port's constant, plain and uncounted
            count_pow_with_constant_exponent(y)
        else:
            if float(x) == 1.0:
                return result  # pow(1, y) is 1.0 for every y: the port's constant, plain and uncounted
            count_pow_with_constant_base(x)
        return float.__new__(CountedFloat, result)
    return original_math_pow(x, y)


def math_fma(x: float, y: float, z: float) -> float | CountedFloat:
    """Patch math.fma: stdlib contract (fused multiply-add, a single rounding).

    This is the one place a fusion is observable from Python, so it is the one place it can be
    counted; `a*b + c` written as operators is invisible to the interpreter and stays MUL + ADD.

    Flop classification follows the constant-folding convention, treating any non-CountedFloat
    operand as a compile-time constant:
      - two constant multiplicands -> their product folds, leaving a compiled port with a bare
                                      add on the remaining runtime value -> ADD; a product of
                                      exactly -0.0 folds the add away too (z + (-0.0) is z for
                                      every z -- cost-model rule 1.7) and counts nothing, where
                                      a +0.0 product keeps the ADD ((-0.0) + 0.0 is +0.0)
      - any other counted operand  -> the port emits one fused instruction -> FMA
    Once an fma survives, constant *values* are never inspected: the explicit call is the author
    asking for the fused instruction, and it stays fused.
    """
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat) or isinstance(z, CountedFloat):
        # computed first: math.fma raises ValueError on invalid operand combinations
        # (e.g. fma(inf, 0.0, z)) and then nothing should be counted
        result = original_math_fma(x, y, z)
        if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
            try:
                _TLS.flop_counts.FMA += 1
            except AttributeError:  # first counted op on this thread
                _create_thread_state().FMA += 1
        else:
            product = x * y  # the constant a compiled port folds at compile time (both multiplicands are plain)
            if product == 0.0 and _copysign(1.0, product) < 0.0:
                # a -0.0 product leaves z + (-0.0), which is z for every z, so the port emits
                # nothing -- the same sign-exact identity fold as a written -0.0 addend
                return float.__new__(CountedFloat, result)
            try:
                _TLS.flop_counts.ADD += 1  # x*y is a constant product; only the add survives folding
            except AttributeError:  # first counted op on this thread
                _create_thread_state().ADD += 1
        return float.__new__(CountedFloat, result)
    return original_math_fma(x, y, z)


def math_sin(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_sin(x)  # compute first: sin(±inf) raises (ValueError) before counting
        try:
            _TLS.flop_counts.SIN += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().SIN += 1
        return float.__new__(CountedFloat, result)
    return original_math_sin(x)


def math_cos(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_cos(x)  # compute first: cos(±inf) raises (ValueError) before counting
        try:
            _TLS.flop_counts.COS += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COS += 1
        return float.__new__(CountedFloat, result)
    return original_math_cos(x)


def math_tan(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_tan(x)  # compute first: tan(±inf) raises (ValueError) before counting
        try:
            _TLS.flop_counts.TAN += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().TAN += 1
        return float.__new__(CountedFloat, result)
    return original_math_tan(x)


def math_asin(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_asin(x)  # compute first: domain errors raise before anything is counted
        try:
            _TLS.flop_counts.ASIN += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ASIN += 1
        return float.__new__(CountedFloat, result)
    return original_math_asin(x)


def math_acos(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_acos(x)  # compute first: domain errors raise before anything is counted
        try:
            _TLS.flop_counts.ACOS += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ACOS += 1
        return float.__new__(CountedFloat, result)
    return original_math_acos(x)


def math_atan(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_atan(x)
        try:
            _TLS.flop_counts.ATAN += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ATAN += 1
        return float.__new__(CountedFloat, result)
    return original_math_atan(x)


def math_atan2(y: float, x: float) -> float | CountedFloat:
    if isinstance(y, CountedFloat) or isinstance(x, CountedFloat):
        result = original_math_atan2(y, x)
        try:
            _TLS.flop_counts.ATAN2 += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ATAN2 += 1
        return float.__new__(CountedFloat, result)
    return original_math_atan2(y, x)


def math_hypot(*coordinates: float) -> float | CountedFloat:
    """Patch math.hypot: stdlib contract (n-ary since Python 3.8), counted per arity.

    Counted as the real overflow-safe algorithm the call executes, at every arity:
      - 2+ coordinates -> HYPOT + (n-2) HYPOT_XARG: the benchmarked 2-argument base cost plus
                          the measured per-extra-coordinate slope of the scaled algorithm
      - 1 coordinate   -> ABS: it computes |x|, and a port emits fabs
    A 2-argument call counts exactly one HYPOT, unchanged from when that was the only
    benchmarked form.
    """
    if not any(isinstance(c, CountedFloat) for c in coordinates):
        return original_math_hypot(*coordinates)
    result = original_math_hypot(*coordinates)
    n = len(coordinates)
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    if n == 1:
        cnt.ABS += 1
    else:
        cnt.HYPOT += 1
        if n > 2:
            cnt.HYPOT_XARG += n - 2
    return float.__new__(CountedFloat, result)


def math_expm1(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_expm1(x)  # compute first: expm1 overflows (OverflowError) before counting
        try:
            _TLS.flop_counts.EXPM1 += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().EXPM1 += 1
        return float.__new__(CountedFloat, result)
    return original_math_expm1(x)


def math_log1p(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_log1p(x)  # compute first: domain error (x <= -1) raises before counting
        try:
            _TLS.flop_counts.LOG1P += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().LOG1P += 1
        return float.__new__(CountedFloat, result)
    return original_math_log1p(x)


def math_fmod(x: float, y: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        result = original_math_fmod(x, y)  # compute first: fmod(x, 0) raises before anything is counted
        try:
            _TLS.flop_counts.FMOD += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().FMOD += 1
        return float.__new__(CountedFloat, result)
    return original_math_fmod(x, y)


def math_remainder(x: float, y: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        result = original_math_remainder(x, y)  # compute first: remainder(x, 0) raises before anything is counted
        try:
            _TLS.flop_counts.REMAINDER += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().REMAINDER += 1
        return float.__new__(CountedFloat, result)
    return original_math_remainder(x, y)


def math_fabs(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_fabs(x)
        try:
            _TLS.flop_counts.ABS += 1  # same FABS/ANDPD instruction as abs(); reuses FlopType.ABS
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ABS += 1
        return float.__new__(CountedFloat, result)
    return original_math_fabs(x)


def math_sinh(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_sinh(x)  # compute first: sinh overflows (OverflowError) before counting
        try:
            _TLS.flop_counts.SINH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().SINH += 1
        return float.__new__(CountedFloat, result)
    return original_math_sinh(x)


def math_cosh(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_cosh(x)  # compute first: cosh overflows (OverflowError) before counting
        try:
            _TLS.flop_counts.COSH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COSH += 1
        return float.__new__(CountedFloat, result)
    return original_math_cosh(x)


def math_tanh(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_tanh(x)
        try:
            _TLS.flop_counts.TANH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().TANH += 1
        return float.__new__(CountedFloat, result)
    return original_math_tanh(x)


def math_asinh(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_asinh(x)
        try:
            _TLS.flop_counts.ASINH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ASINH += 1
        return float.__new__(CountedFloat, result)
    return original_math_asinh(x)


def math_acosh(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_acosh(x)  # compute first: domain error (x < 1) raises before counting
        try:
            _TLS.flop_counts.ACOSH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ACOSH += 1
        return float.__new__(CountedFloat, result)
    return original_math_acosh(x)


def math_atanh(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_atanh(x)  # compute first: domain error (|x| >= 1) raises before counting
        try:
            _TLS.flop_counts.ATANH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ATANH += 1
        return float.__new__(CountedFloat, result)
    return original_math_atanh(x)


def math_gamma(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_gamma(
            x
        )  # compute first: gamma's poles (0, -1, -2, ...) and overflow raise before counting
        try:
            _TLS.flop_counts.GAMMA += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().GAMMA += 1
        return float.__new__(CountedFloat, result)
    return original_math_gamma(x)


def math_lgamma(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_lgamma(x)  # compute first: lgamma's poles raise before counting
        try:
            _TLS.flop_counts.LGAMMA += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().LGAMMA += 1
        return float.__new__(CountedFloat, result)
    return original_math_lgamma(x)


def math_erf(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_erf(x)
        try:
            _TLS.flop_counts.ERF += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ERF += 1
        return float.__new__(CountedFloat, result)
    return original_math_erf(x)


def math_erfc(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_erfc(x)
        try:
            _TLS.flop_counts.ERFC += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ERFC += 1
        return float.__new__(CountedFloat, result)
    return original_math_erfc(x)


def math_degrees(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_degrees(x)
        try:
            _TLS.flop_counts.MUL += 1  # x * (180/pi), the constant folded at compile time
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, result)
    return original_math_degrees(x)


def math_radians(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        result = original_math_radians(x)
        try:
            _TLS.flop_counts.MUL += 1  # x * (pi/180), the constant folded at compile time
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, result)
    return original_math_radians(x)


def math_dist(p: Iterable[float], q: Iterable[float]) -> float | CountedFloat:
    """Patch math.dist: stdlib contract, counted as the overflow-safe algorithm it executes.

    Counted as DIST + (n-2) DIST_XARG for n-dimensional inputs: the benchmarked 2-D base cost
    (which carries the per-coordinate subtractions in its offset) plus the measured
    per-extra-coordinate slope. 1-D inputs count SUB + ABS instead: the call computes
    |p0 - q0| through the same single-coordinate shortcut 1-argument hypot takes, so the
    port pays the subtract and the fabs, not the scaled 2-D machinery. Iterator inputs are
    materialized up front (the stdlib accepts them too), so the coordinates can be inspected
    after computing the result.
    """
    p_seq = list(p)
    q_seq = list(q)
    # computed first: raises per stdlib contract (unequal lengths, non-numbers) before counting
    result = original_math_dist(p_seq, q_seq)
    if not any(isinstance(c, CountedFloat) for c in (*p_seq, *q_seq)):
        return result
    n = len(p_seq)
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    if n == 1:
        cnt.SUB += 1
        cnt.ABS += 1
    else:
        cnt.DIST += 1
        if n > 2:
            cnt.DIST_XARG += n - 2
    return float.__new__(CountedFloat, result)


def math_prod(iterable: Iterable[float], /, *, start: float = 1) -> float | CountedFloat:
    """Patch math.prod: stdlib contract, counted as the multiply loop a port emits.

    Counts n-1 MUL for n elements, and n when `start` is a CountedFloat (a runtime value, so
    its multiply is real) or differs from 1: a port seeds its accumulator from the first
    element, so only a start it cannot fold opens the loop with a multiply. No element folds,
    unlike the constant folds of cost-model rule 1.7 -- the port's loop body runs once per
    element whatever value that element holds.

    Counted inputs are unboxed before delegating, so the original's own multiplications register
    nothing; inputs without any CountedFloat are delegated wholesale, preserving int-exactness.
    """
    values = list(iterable)
    if not isinstance(start, CountedFloat) and not any(isinstance(v, CountedFloat) for v in values):
        return original_math_prod(values, start=start)
    plain_values = [float(v) if isinstance(v, CountedFloat) else v for v in values]
    plain_start = float(start) if isinstance(start, CountedFloat) else start
    # computed first: raises per stdlib contract (non-numeric elements) before anything is counted
    result = original_math_prod(plain_values, start=plain_start)
    opens_with_multiply = isinstance(start, CountedFloat) or start != 1
    n_muls = len(values) if opens_with_multiply else len(values) - 1
    if n_muls:
        try:
            _TLS.flop_counts.MUL += n_muls
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += n_muls
    return float.__new__(CountedFloat, result)


def math_fsum(seq: Iterable[float]) -> float | CountedFloat:
    """Patch math.fsum: stdlib contract (Shewchuk exact summation), counted as (n-1) ADD.

    Counts the mathematical reduction, knowingly under-counting fsum's compensation machinery:
    the exact-summation partials grow and shrink with the data, so the real cost has no per-call
    constant to price -- the input-dependent-cost fallback in the cost-model docs
    (docs/cost_model.md). A prototype that wants compensation costed can write Kahan out in
    operators and have it counted exactly. The value is computed by the original, so fsum's
    exactness is untouched.
    """
    values = list(seq)
    result = original_math_fsum(values)
    if not any(isinstance(v, CountedFloat) for v in values):
        return result
    try:
        _TLS.flop_counts.ADD += len(values) - 1
    except AttributeError:  # first counted op on this thread
        _create_thread_state().ADD += len(values) - 1
    return float.__new__(CountedFloat, result)


def math_sumprod(p: Iterable[float], q: Iterable[float], /) -> float | CountedFloat:
    """Patch math.sumprod: stdlib contract, counted as the extended-precision algorithm it runs.

    CPython's compensated (TripleLength) accumulation is gated on exact-float elements, so
    counted inputs are unboxed to plain floats before delegating -- a CountedFloat anywhere in
    the inputs would silently reroute the whole call to the generic object path, computing the
    *naive* sum of products. Counted as SUMPROD + (n-2) SUMPROD_XELEM for n-element inputs:
    the benchmarked 2-element base (close-out included) plus the measured per-extra-element
    slope; a 1-element call counts the base alone. Both iterables are materialized up front
    (the stdlib accepts one-shot iterators too), and inputs without any CountedFloat are
    delegated to the original wholesale (preserving its int-exactness and fast paths).
    """
    p_values = list(p)
    q_values = list(q)
    if not any(isinstance(v, CountedFloat) for v in (*p_values, *q_values)):
        return original_math_sumprod(p_values, q_values)
    p_plain = [float(v) if isinstance(v, CountedFloat) else v for v in p_values]
    q_plain = [float(v) if isinstance(v, CountedFloat) else v for v in q_values]
    # computed first: raises per stdlib contract (unequal lengths, non-numbers) before counting
    result = original_math_sumprod(p_plain, q_plain)
    n = len(p_values)
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    cnt.SUMPROD += 1
    if n > 2:
        cnt.SUMPROD_XELEM += n - 2
    return float.__new__(CountedFloat, result)


def math_copysign(x: float, y: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        result = original_math_copysign(x, y)
        try:
            _TLS.flop_counts.COPYSIGN += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COPYSIGN += 1
        return float.__new__(CountedFloat, result)
    return original_math_copysign(x, y)


def math_fmax(x: float, y: float, /) -> float | CountedFloat:
    """Patch math.fmax: stdlib contract (NaN-quieting maximum), counted as one COMP.

    A port emits the IEEE max instruction (ARM's `fmaxnm`) -- one instruction of the same
    compare-select class the COMP weight measures, so the weight is reused, as `math.fabs`
    reuses ABS. The builtin `max` shares that price while being a different value function:
    a comparison chain returning whichever operand survives, order-dependent under NaN,
    where fmax is the NaN-quieting selection. Stated gap: the NaN-quieting clause is a
    guard, and guards go unpriced, so one COMP is charged on every regime.

    No constant fold applies at any operand value. The candidates all fail the sign- and
    nan-exactness test: `fmax(x, -inf)` is `x` for every x except a NaN, where it is `-inf`,
    and `fmax(x, nan)` leaves a signaling NaN quieted rather than untouched.
    """
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        result = original_math_fmax(x, y)
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return float.__new__(CountedFloat, result)
    return original_math_fmax(x, y)


def math_fmin(x: float, y: float, /) -> float | CountedFloat:
    """Patch math.fmin: stdlib contract (NaN-quieting minimum), counted as one COMP.

    The mirror of math_fmax in every respect -- same canonical compare-and-select, same
    unpriced NaN guard, same absence of folds.
    """
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        result = original_math_fmin(x, y)
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return float.__new__(CountedFloat, result)
    return original_math_fmin(x, y)


def math_isnan(x: float) -> bool:
    """Patch math.isnan: counted as the one FP self-compare a port emits.

    The C classifier compiles to `ucomisd x, x` / `fcmp d, d` plus a flag read on both priced
    architectures -- exactly the compare-and-select machinery the COMP weight measures, and the
    machine work of the counted spelling `x != x`.
    """
    if isinstance(x, CountedFloat):
        result = original_math_isnan(x)
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result
    return original_math_isnan(x)


def math_isinf(x: float) -> bool:
    """Patch math.isinf: counted ABS + COMP, the FP-canonical `fabs(x) == inf`.

    Priced from the FP-canonical form even though some compilers lower the classifier to integer
    bit tests on some targets: the model prices one instruction stream for every architecture,
    and a value-level FP operation keeps its price whatever bit tricks implement it (the same
    stance as copysign's benchmarked weight).
    """
    if isinstance(x, CountedFloat):
        result = original_math_isinf(x)
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.ABS += 1
        cnt.COMP += 1
        return result
    return original_math_isinf(x)


def math_isfinite(x: float) -> bool:
    """Patch math.isfinite: counted ABS + COMP, the FP-canonical `fabs(x) < inf`.

    Same pricing stance as isinf: the FP-canonical instruction stream, whatever
    integer-domain lowering a particular compiler picks.
    """
    if isinstance(x, CountedFloat):
        result = original_math_isfinite(x)
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.ABS += 1
        cnt.COMP += 1
        return result
    return original_math_isfinite(x)


def math_isclose(a: float, b: float, **kwargs: float) -> bool:
    """Patch math.isclose: counted as the transcription of its documented defining formula.

    The stdlib contract is `abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)`, which
    transcribes symbol by symbol (max -> COMP, the model's min/max price) to
    SUB + 3 ABS + MUL + 3 COMP -- fixed per call by construction, charged whatever branch the
    implementation actually takes. Stated gaps under the cost model's formula rule: the
    `a == b` and infinity guards, the `||` short-circuit savings, and the implementation's
    weak-test respelling (CPython multiplies twice, `fabs(rel_tol*b)` and `fabs(rel_tol*a)`,
    where the formula's max-then-multiply does once). Tolerances arrive by keyword (mirrored
    here), and a CountedFloat anywhere among the operands counts the call.
    """
    # computed first: a non-numeric operand or negative tolerance raises before counting
    result = original_math_isclose(a, b, **kwargs)
    if (
        isinstance(a, CountedFloat)
        or isinstance(b, CountedFloat)
        or any(isinstance(v, CountedFloat) for v in kwargs.values())
    ):
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.SUB += 1
        cnt.ABS += 3
        cnt.MUL += 1
        cnt.COMP += 3
    return result


def math_isnormal(x: float, /) -> bool:
    """Patch math.isnormal: counted ABS + 2 COMP, the FP-canonical `DBL_MIN <= fabs(x) <= DBL_MAX`.

    Same pricing stance as isinf and isfinite: the FP-canonical instruction stream, whatever
    integer-domain lowering a particular compiler picks. The upper bound is isfinite's own
    test, so isnormal prices as isfinite plus the one comparison that separates normals from
    subnormals, with the magnitude taken once. Stated gap: the price is fixed per call because
    the port is branchless, so it over-charges the Python spelling on every input where the
    chained comparison short-circuits (zeros, subnormals and NaN stop after one compare).
    """
    if isinstance(x, CountedFloat):
        result = original_math_isnormal(x)
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.ABS += 1
        cnt.COMP += 2
        return result
    return original_math_isnormal(x)


def math_issubnormal(x: float, /) -> bool:
    """Patch math.issubnormal: counted ABS + 2 COMP, the FP-canonical `0.0 < fabs(x) < DBL_MIN`.

    The mirror of isnormal on the other side of the same boundary: one magnitude and two
    bounds, the lower one excluding zero (which is neither normal nor subnormal). Its stated
    gap is isnormal's -- fixed per call against a spelling that short-circuits on zeros and NaN.
    """
    if isinstance(x, CountedFloat):
        result = original_math_issubnormal(x)
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.ABS += 1
        cnt.COMP += 2
        return result
    return original_math_issubnormal(x)


def math_signbit(x: float, /) -> bool:
    """Patch math.signbit: counted as one COMP, the price of reading one bool off one float.

    Alone among the classifiers this one has no FP decomposition to transcribe. `x < 0.0` is
    not it -- `signbit(-0.0)` is True where the comparison is False -- and the only faithful
    float spelling, `copysign(1.0, x) < 0.0`, needs its copysign solely to make the sign
    visible to a comparison. That copysign is machinery the spelling needs, not work the
    operation does, so it is not priced; what remains is the float-domain exit every classifier
    pays for materializing its bool.
    """
    if isinstance(x, CountedFloat):
        result = original_math_signbit(x)
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result
    return original_math_signbit(x)


# -------------------------------------------------------------------------
#  replacements for what cannot be counted
# -------------------------------------------------------------------------
# The math functions that meet CountedFloat values without counting them, mapped to what each such
# call costs the count.  Kept in step with the coverage table in the math-patching docs: the
# not-instrumented functions hand back plain floats, which stops counting downstream.  Their
# replacements only report -- the results are the originals', untouched.
_BREAKS_CONTAGION = "uncounted; result is a plain float"
_UNCOUNTED_MATH: dict[str, str] = {
    "frexp": _BREAKS_CONTAGION,
    "ldexp": _BREAKS_CONTAGION,
    "modf": _BREAKS_CONTAGION,
    "nextafter": _BREAKS_CONTAGION,
    "ulp": _BREAKS_CONTAGION,
}
# Delegation targets of the replacements below.  Captured when they are installed — a replacement
# can only be executing at or after that capture — and, like the counting replacements' originals,
# never cleared: a call already executing a replacement must still find the function to delegate
# to, even if the last reporting thread finishes meanwhile.
_uncounted_originals: dict[str, Callable[..., object]] = {}


def _make_uncounted_wrapper(name: str, consequence: str) -> Callable[..., object]:
    """Build the report-and-delegate replacement for one uninstrumented math function.

    Args:
        name: Name of the math function to replace.
        consequence: What the missing count costs, for the reported line.

    Returns:
        A replacement that reports the call while the calling thread is reporting, and otherwise
        behaves exactly like the function it replaces.
    """

    def replacement(*args: object, **kwargs: object) -> object:
        # the thread's reporting state is tested first: it settles the question for every thread
        # that is not reporting -- one that never counted, runs at level OFF, or is paused (paused
        # operations are deliberately uncounted, so they are not warned about either) -- without
        # walking the arguments.  Keyword values are scanned too: math.isclose takes its
        # tolerances by keyword, and a CountedFloat there is as unseen by the count as one in a
        # positional slot.
        if thread_is_reporting() and any(isinstance(arg, CountedFloat) for arg in (*args, *kwargs.values())):
            warn_uncounted_call(name, consequence)
        return _uncounted_originals[name](*args, **kwargs)

    return replacement


# Kept out of _PATCHES deliberately: these are installed only while some thread is reporting (see
# apply_uncounted_math_patches), so a run at the default verbosity leaves these functions exactly
# as it found them rather than routing every call through a replacement that has nothing to say.
_UNCOUNTED_PATCHES: dict[str, Callable[..., object]] = {
    name: _make_uncounted_wrapper(name, consequence) for name, consequence in _UNCOUNTED_MATH.items()
}


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
    "asin": math_asin,
    "acos": math_acos,
    "atan": math_atan,
    "atan2": math_atan2,
    "hypot": math_hypot,
    "expm1": math_expm1,
    "log1p": math_log1p,
    "fmod": math_fmod,
    "fabs": math_fabs,
    "sinh": math_sinh,
    "cosh": math_cosh,
    "tanh": math_tanh,
    "asinh": math_asinh,
    "acosh": math_acosh,
    "atanh": math_atanh,
    "degrees": math_degrees,
    "radians": math_radians,
    "dist": math_dist,
    "prod": math_prod,
    "fsum": math_fsum,
    "copysign": math_copysign,
    "gamma": math_gamma,
    "lgamma": math_lgamma,
    "erf": math_erf,
    "erfc": math_erfc,
    "remainder": math_remainder,
    "isnan": math_isnan,
    "isinf": math_isinf,
    "isfinite": math_isfinite,
    "isclose": math_isclose,
}
if hasattr(math, "fma"):
    # Python 3.13+ only. Registering conditionally is what keeps every loop over _PATCHES --
    # capture, apply, restore -- free of version checks of its own.
    _PATCHES["fma"] = math_fma
if hasattr(math, "sumprod"):
    # Python 3.12+ only; same conditional-registration reasoning as math.fma above.
    _PATCHES["sumprod"] = math_sumprod
# The 3.15 additions, gated one by one on the same reasoning: a partition that is exact on
# every interpreter needs each name registered where that name exists, not where its release
# did.
if hasattr(math, "fmax"):
    _PATCHES["fmax"] = math_fmax
if hasattr(math, "fmin"):
    _PATCHES["fmin"] = math_fmin
if hasattr(math, "isnormal"):
    _PATCHES["isnormal"] = math_isnormal
if hasattr(math, "issubnormal"):
    _PATCHES["issubnormal"] = math_issubnormal
if hasattr(math, "signbit"):
    _PATCHES["signbit"] = math_signbit

# Why each remaining public `math` callable needs no replacement of either kind.  Between this,
# _PATCHES and _UNCOUNTED_MATH the whole module surface is accounted for, and a test holds them to
# that -- so a float function a future CPython adds to `math` fails there rather than becoming a
# silently uncounted hole.  The reason per entry is a judgment about the function's domain that
# nothing about the callable itself reveals, which is why they are listed rather than detected.
_NOT_PATCHED_DUNDER = "counted already, through the CountedFloat dunder it dispatches to"
_NOT_PATCHED_INTEGER_DOMAIN = "integer domain: never operates on floats"
_MATH_NOT_PATCHED: dict[str, str] = {
    "floor": _NOT_PATCHED_DUNDER,
    "ceil": _NOT_PATCHED_DUNDER,
    "trunc": _NOT_PATCHED_DUNDER,
    "comb": _NOT_PATCHED_INTEGER_DOMAIN,
    "factorial": _NOT_PATCHED_INTEGER_DOMAIN,
    "gcd": _NOT_PATCHED_INTEGER_DOMAIN,
    "isqrt": _NOT_PATCHED_INTEGER_DOMAIN,
    "lcm": _NOT_PATCHED_INTEGER_DOMAIN,
    "perm": _NOT_PATCHED_INTEGER_DOMAIN,
}

# the module-global holding each patched function's delegation target, resolved once at import so
# re-capture does no string work of its own. Derived from _PATCHES, hence built after the
# version-gated entries have been registered above.
_REFERENCE_NAMES: dict[str, str] = {name: f"{_REFERENCE_PREFIX}{name}" for name in _PATCHES}

# the math functions saved at patch time, to be restored at unpatch time
_saved_originals: dict[str, object] = {}

# number of currently active FlopCountingContext instances; patches are applied on the 0->1
# transition and removed on the 1->0 transition, so nested contexts behave correctly
# (guarded by _patch_lock: concurrent first-entries must not double-capture or interleave
#  capture with patch application)
_active_context_count = 0

# number of threads currently reporting; the reporting replacements are installed on the 0->1
# transition and removed on the 1->0 one, so they exist only while someone is listening
_reporting_thread_count = 0

_patch_lock = threading.Lock()


def _capture_originals() -> None:
    """Snapshot the current math functions, for delegation and for restoring on unpatch.

    Two views of the same snapshot, because they are read very differently. `_saved_originals` is a
    dict, walked once per unpatch. The `original_math_*` module globals are what the replacements
    themselves call, on every delegated call -- a module-global read, which measures meaningfully
    cheaper than a dict lookup, and is why those names exist at all.

    Rebinding them through `globals()` is what keeps that list of names from being written out a
    second and third time here: `globals()` *is* this module's namespace, so an update to it is seen
    by every already-defined replacement. Only the names in `_PATCHES` are re-captured, which is
    also what makes the plain `getattr` safe -- a version-gated function absent from this
    interpreter is absent from `_PATCHES` too, and keeps the stand-in bound at import.

    The snapshot deliberately takes whatever is current rather than the stdlib original: another
    package may have patched `math` after we were imported, and we delegate through -- and later
    restore -- its patches rather than silently wiping them.
    """
    _saved_originals.clear()
    captured: dict[str, object] = {}
    for name, reference in _REFERENCE_NAMES.items():
        current = getattr(math, name)
        _saved_originals[name] = current
        captured[reference] = current
    globals().update(captured)


def apply_math_patches() -> None:
    """Apply the counting replacements to the math module (refcounted; see module docstring)."""
    global _active_context_count
    with _patch_lock:
        _active_context_count += 1
        if _active_context_count == 1:
            _capture_originals()
            for name, replacement in _PATCHES.items():
                setattr(math, name, replacement)


def remove_math_patches() -> None:
    """Undo apply_math_patches; the math module is restored once the last context exits."""
    global _active_context_count
    with _patch_lock:
        if _active_context_count == 0:
            # nothing is patched, so there is nothing to undo.  Restoring here would re-apply a
            # snapshot taken before the last context exited, silently overwriting whatever has
            # patched math since.
            return
        _active_context_count -= 1
        if _active_context_count == 0:
            # restore the snapshot unconditionally, assuming LIFO patching discipline of any other
            # patching packages (see module docstring for the exact contract)
            for name, saved in _saved_originals.items():
                setattr(math, name, saved)
            _saved_originals.clear()


def apply_uncounted_math_patches() -> None:
    """Install the reporting replacements (refcounted; see module docstring).

    Called when a thread starts reporting.  The replacements stay installed until the last such
    thread stops, which is always inside the with-block of the context that made it report — so
    this patch set's lifetime is strictly nested inside the counting replacements'.
    """
    global _reporting_thread_count
    with _patch_lock:
        _reporting_thread_count += 1
        if _reporting_thread_count == 1:
            for name, replacement in _UNCOUNTED_PATCHES.items():
                _uncounted_originals[name] = getattr(math, name)
                setattr(math, name, replacement)


def remove_uncounted_math_patches() -> None:
    """Undo apply_uncounted_math_patches; restored once the last reporting thread stops."""
    global _reporting_thread_count
    with _patch_lock:
        if _reporting_thread_count == 0:
            return  # nothing is installed, so there is nothing to undo
        _reporting_thread_count -= 1
        if _reporting_thread_count == 0:
            for name, original in _uncounted_originals.items():
                setattr(math, name, original)
