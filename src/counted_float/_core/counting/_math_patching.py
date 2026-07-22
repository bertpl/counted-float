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
from typing import TYPE_CHECKING

from ._counted_float import CountedFloat, count_pow_with_constant_base, count_pow_with_constant_exponent
from ._thread_counter import _TLS, _create_thread_state, thread_is_reporting
from .verbosity import warn_uncounted_call

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from ._thread_counter import CountsTarget


def _math_fma_unavailable(x: float, y: float, z: float) -> float:
    """Stand-in for `math.fma` on interpreters predating it (below 3.13).

    Never called: the counting replacement is registered only where `math.fma` exists (see
    _PATCHES). It exists so the `original_math_fma` reference is callable on every supported
    interpreter rather than `None`, which would make the patch's own call sites unsound.
    """
    raise NotImplementedError("math.fma requires Python 3.13 or newer")


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
original_math_gamma = math.gamma
original_math_lgamma = math.lgamma
original_math_erf = math.erf
original_math_erfc = math.erfc
original_math_remainder = math.remainder

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
        try:
            _TLS.flop_counts.CBRT += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().CBRT += 1
        return float.__new__(CountedFloat, original_math_cbrt(x))
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
                                  folded at compile time)
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
            cnt.note("const base -> log(x) * 1/log(base)")
            cnt.LOG += 1
            cnt.MUL += 1
    if isinstance(x, CountedFloat) or isinstance(base, CountedFloat):
        return float.__new__(CountedFloat, result)
    return result


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
            count_pow_with_constant_exponent(y)
        else:
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
                                      add on the remaining runtime value -> ADD
      - any other counted operand  -> the port emits one fused instruction -> FMA
    Constant *values* are never inspected: unlike POW, no FMA variant is cheaper than another --
    every one is a single instruction -- so there is nothing to strength-reduce.
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
        try:
            _TLS.flop_counts.ATAN += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ATAN += 1
        return float.__new__(CountedFloat, original_math_atan(x))
    return original_math_atan(x)


def math_atan2(y: float, x: float) -> float | CountedFloat:
    if isinstance(y, CountedFloat) or isinstance(x, CountedFloat):
        try:
            _TLS.flop_counts.ATAN2 += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ATAN2 += 1
        return float.__new__(CountedFloat, original_math_atan2(y, x))
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
        try:
            _TLS.flop_counts.ABS += 1  # same FABS/ANDPD instruction as abs(); reuses FlopType.ABS
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ABS += 1
        return float.__new__(CountedFloat, original_math_fabs(x))
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
        try:
            _TLS.flop_counts.TANH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().TANH += 1
        return float.__new__(CountedFloat, original_math_tanh(x))
    return original_math_tanh(x)


def math_asinh(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        try:
            _TLS.flop_counts.ASINH += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ASINH += 1
        return float.__new__(CountedFloat, original_math_asinh(x))
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
        try:
            _TLS.flop_counts.MUL += 1  # x * (180/pi), the constant folded at compile time
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, original_math_degrees(x))
    return original_math_degrees(x)


def math_radians(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        try:
            _TLS.flop_counts.MUL += 1  # x * (pi/180), the constant folded at compile time
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, original_math_radians(x))
    return original_math_radians(x)


def math_dist(p: Iterable[float], q: Iterable[float]) -> float | CountedFloat:
    """Patch math.dist: stdlib contract, counted as the overflow-safe algorithm it executes.

    Counted as DIST + (n-2) DIST_XARG for n-dimensional inputs: the benchmarked 2-D base cost
    (which carries the per-coordinate subtractions in its offset) plus the measured
    per-extra-coordinate slope. 1-D inputs count the base cost alone. Iterator inputs are
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
    cnt.DIST += 1
    if n > 2:
        cnt.DIST_XARG += n - 2
    return float.__new__(CountedFloat, result)


def math_prod(iterable: Iterable[float], /, *, start: float = 1) -> float | CountedFloat:
    """Patch math.prod: stdlib contract, counted as the multiply chain it computes.

    The product is folded left-to-right with real multiplications, so counting and contagion
    emerge from the operations themselves — mixed inputs count exactly what writing the chain
    out would. A start equal to 1 (the default) is the multiplicative identity: a compiled port
    folds it away, so it opens the chain without a counted multiply — unless it is itself a
    CountedFloat, a runtime value whose multiply is real. Inputs without any CountedFloat are
    delegated to the original wholesale (preserving its int-exactness and fast paths).
    """
    values = list(iterable)
    if not isinstance(start, CountedFloat) and not any(isinstance(v, CountedFloat) for v in values):
        return original_math_prod(values, start=start)
    if isinstance(start, CountedFloat) or start != 1:
        acc, remaining = start, values
    elif values:
        acc, remaining = values[0], values[1:]
    else:
        return start
    for value in remaining:
        acc = acc * value
    return acc


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


def math_copysign(x: float, y: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat) or isinstance(y, CountedFloat):
        try:
            _TLS.flop_counts.COPYSIGN += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COPYSIGN += 1
        return float.__new__(CountedFloat, original_math_copysign(x, y))
    return original_math_copysign(x, y)


# -------------------------------------------------------------------------
#  replacements for what cannot be counted
# -------------------------------------------------------------------------
# The math functions that meet CountedFloat values without counting them, mapped to what each such
# call costs the count.  Kept in step with the coverage table in the math-patching docs: the
# not-instrumented functions hand back plain floats, which stops counting downstream, while
# isclose is the one predicate whose uncounted work is real arithmetic rather than a
# classification.  Their replacements only report -- the results are the originals', untouched.
_BREAKS_CONTAGION = "uncounted; result is a plain float"
_UNCOUNTED_MATH: dict[str, str] = {
    "frexp": _BREAKS_CONTAGION,
    "ldexp": _BREAKS_CONTAGION,
    "modf": _BREAKS_CONTAGION,
    "nextafter": _BREAKS_CONTAGION,
    "ulp": _BREAKS_CONTAGION,
    "isclose": "uncounted; performs real arithmetic",
}
# math.sumprod exists from Python 3.12; on older interpreters there is no call to report on
if hasattr(math, "sumprod"):
    _UNCOUNTED_MATH["sumprod"] = _BREAKS_CONTAGION

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


def _make_uncounted_sumprod_wrapper(name: str, consequence: str) -> Callable[..., object]:
    """Build the report-and-delegate replacement for math.sumprod.

    sumprod takes two *iterables*, so the CountedFloat scan must look at their elements rather
    than at the arguments themselves. While the thread is reporting, both iterables are
    materialized first (consuming a one-shot iterator twice would otherwise hand the original
    empty sequences) and the delegation uses the materialized lists; outside reporting the call
    passes through untouched.
    """

    def replacement(*args: object, **kwargs: object) -> object:
        if not thread_is_reporting():
            return _uncounted_originals[name](*args, **kwargs)
        materialized = [
            list(arg)  # ty: ignore[invalid-argument-type] -- sumprod's positional args are iterables
            for arg in args
        ]
        if any(isinstance(value, CountedFloat) for seq in materialized for value in seq):
            warn_uncounted_call(name, consequence)
        return _uncounted_originals[name](*materialized, **kwargs)

    return replacement


# Kept out of _PATCHES deliberately: these are installed only while some thread is reporting (see
# apply_uncounted_math_patches), so a run at the default verbosity leaves these functions exactly
# as it found them rather than routing every call through a replacement that has nothing to say.
_UNCOUNTED_PATCHES: dict[str, Callable[..., object]] = {
    name: (
        _make_uncounted_sumprod_wrapper(name, consequence)
        if name == "sumprod"
        else _make_uncounted_wrapper(name, consequence)
    )
    for name, consequence in _UNCOUNTED_MATH.items()
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
}
if hasattr(math, "fma"):
    # Python 3.13+ only. Registering conditionally is what keeps every loop over _PATCHES --
    # capture, apply, restore -- free of version checks of its own.
    _PATCHES["fma"] = math_fma
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
    """Snapshot the current math functions.

    This way the replacements delegate through (and unpatching restores) whatever is current —
    possibly another package's patches, not the stdlib originals.
    """
    global original_math_sqrt, original_math_cbrt, original_math_log, original_math_log2
    global original_math_log10, original_math_exp, original_math_exp2, original_math_pow, original_math_fma
    global original_math_sin, original_math_cos, original_math_tan
    global original_math_asin, original_math_acos, original_math_atan, original_math_atan2
    global original_math_hypot, original_math_expm1, original_math_log1p, original_math_fmod, original_math_fabs
    global original_math_sinh, original_math_cosh, original_math_tanh
    global original_math_asinh, original_math_acosh, original_math_atanh
    global original_math_degrees, original_math_radians, original_math_dist
    global original_math_prod, original_math_fsum, original_math_copysign
    global original_math_gamma, original_math_lgamma, original_math_erf, original_math_erfc
    global original_math_remainder

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
    original_math_gamma = math.gamma
    original_math_lgamma = math.lgamma
    original_math_erf = math.erf
    original_math_erfc = math.erfc
    original_math_remainder = math.remainder

    _saved_originals.clear()
    for name in _PATCHES:
        _saved_originals[name] = getattr(math, name)


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
