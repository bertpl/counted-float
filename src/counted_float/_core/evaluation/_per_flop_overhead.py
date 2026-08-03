"""Per-flop-type overhead loops: a float/CountedFloat timed-loop pair for every measurable FlopType.

Each loop applies one operation to a pre-generated pool of in-domain operands, so both variants run
line-for-line identical Python and differ only in whether the measured operand is wrapped in
CountedFloat. The counted variant runs inside an open FlopCountingContext, because `math.*` calls
are only patched -- and therefore only counted -- while one is open; operator counting works
everywhere, but the context keeps every loop measuring the configuration a counting user actually
runs. The measured ratio includes the loop's per-iteration scaffolding, which is identical in both
variants -- the overhead a pure-Python workload experiences, not the bare dispatch cost.

Operand pools keep every loop on the generic counting path: values sit strictly inside each
operation's domain and never hit a constant fold or strength reduction (no +-0.0 addends, +-1.0
multipliers, power-of-two divisors, or special exponents). The one exception is EXP10, whose only
counted spelling *is* the constant-base fold `10.0 ** x` -- its expression column states exactly
that. Types with no reliably measurable standalone loop are listed by excluded_flop_types() with
the reason, so the printed report shows the exemptions rather than silently omitting rows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from counted_float._core.counting import CountedFloat, FlopCountingContext
from counted_float._core.micro_benchmarking import MicroBenchmark
from counted_float._core.models import FlopType

if TYPE_CHECKING:
    from collections.abc import Callable

# A pool's element schema varies per loop (single operands, operand tuples, 2-element points,
# constructor pairs), so pools type as list[Any] and each loop body unpacks its own schema
_Pool = list[Any]


# =================================================================================================
#  Operand pools
# =================================================================================================
_POOL_SIZE = 256


def _spread(lo: float, hi: float) -> list[float]:
    """Evenly spaced interval midpoints strictly inside (lo, hi).

    Deterministic (captures are reproducible up to timing noise) and safely clear of the exact
    special values the fold and strength-reduction checks key on.
    """
    width = hi - lo
    return [lo + width * (2 * i + 1) / (2 * _POOL_SIZE) for i in range(_POOL_SIZE)]


def _wrapped(values: list[float], counted: bool) -> _Pool:
    """The measured-operand stream: wrapped in CountedFloat for the counted variant."""
    return [CountedFloat(v) for v in values] if counted else list(values)


def _unary_pool(lo: float, hi: float) -> Callable[[bool], _Pool]:
    """Build a pool factory of single measured operands in (lo, hi)."""

    def make(counted: bool) -> _Pool:
        return _wrapped(_spread(lo, hi), counted)

    return make


def _pair_pool(lo: float, hi: float) -> Callable[[bool], _Pool]:
    """Build a pool factory of (x, y) pairs: x is the measured operand, y stays a plain float."""

    def make(counted: bool) -> _Pool:
        xs = _wrapped(_spread(lo, hi), counted)
        ys = _spread(lo + 0.05, hi - 0.05)
        return list(zip(xs, ys, strict=True))

    return make


def _triple_pool(lo: float, hi: float) -> Callable[[bool], _Pool]:
    """Build a pool factory of (x, y, z) triples: x is the measured operand, y and z plain floats."""

    def make(counted: bool) -> _Pool:
        xs = _wrapped(_spread(lo, hi), counted)
        ys = _spread(lo + 0.05, hi - 0.05)
        zs = _spread(lo + 0.11, hi - 0.11)
        return list(zip(xs, ys, zs, strict=True))

    return make


def _point_pair_pool(lo: float, hi: float) -> Callable[[bool], _Pool]:
    """Build a pool factory of (p, q) pairs of 2-element points; p's first coordinate is measured."""

    def make(counted: bool) -> _Pool:
        xs = _wrapped(_spread(lo, hi), counted)
        x2s = _spread(lo + 0.03, hi - 0.03)
        y1s = _spread(lo + 0.07, hi - 0.07)
        y2s = _spread(lo + 0.13, hi - 0.13)
        return [((x, x2), (y1, y2)) for x, x2, y1, y2 in zip(xs, x2s, y1s, y2s, strict=True)]

    return make


def _int_constructor_pool() -> Callable[[bool], _Pool]:
    """Build a pool factory of (constructor, i) pairs for the int-to-float conversion loop.

    I2F is counted at construction from an int, so the operation the two variants share is "build
    a float-family value from this int" -- float(i) for the baseline, CountedFloat(i) for the
    counted variant -- with the constructor carried in the pool so the loop body stays identical.
    """

    def make(counted: bool) -> _Pool:
        constructor = CountedFloat if counted else float
        return [(constructor, 3 + 5 * i) for i in range(_POOL_SIZE)]

    return make


# =================================================================================================
#  Per-type loop bodies
# =================================================================================================
# One tiny function per measured type, so each loop's bytecode contains exactly its own operation.
# Shared contract: one operation per pool element, result discarded; the docstring names the
# expression, the pool provides in-domain operands for it.
def _loop_abs(pool: _Pool) -> None:
    """One `abs(x)` per pool element."""
    for x in pool:
        _ = abs(x)


def _loop_minus(pool: _Pool) -> None:
    """One `-x` per pool element."""
    for x in pool:
        _ = -x


def _loop_copysign(pool: _Pool) -> None:
    """One `math.copysign(x, y)` per pool element."""
    for x, y in pool:
        _ = math.copysign(x, y)


def _loop_comp(pool: _Pool) -> None:
    """One `x <= y` per pool element."""
    for x, y in pool:
        _ = x <= y


def _loop_rnd(pool: _Pool) -> None:
    """One `round(x, 0)` per pool element."""
    for x in pool:
        _ = round(x, 0)


def _loop_f2i(pool: _Pool) -> None:
    """One `int(x)` per pool element."""
    for x in pool:
        _ = int(x)


def _loop_i2f(pool: _Pool) -> None:
    """One constructor-from-int call per pool element."""
    for constructor, i in pool:
        _ = constructor(i)


def _loop_add(pool: _Pool) -> None:
    """One `x + y` per pool element."""
    for x, y in pool:
        _ = x + y


def _loop_sub(pool: _Pool) -> None:
    """One `x - y` per pool element."""
    for x, y in pool:
        _ = x - y


def _loop_mul(pool: _Pool) -> None:
    """One `x * y` per pool element."""
    for x, y in pool:
        _ = x * y


def _loop_div(pool: _Pool) -> None:
    """One `x / y` per pool element."""
    for x, y in pool:
        _ = x / y


def _loop_fma(pool: _Pool) -> None:
    """One `math.fma(x, y, z)` per pool element."""
    for x, y, z in pool:
        _ = math.fma(x, y, z)  # ty: ignore[unresolved-attribute] -- registered only where math.fma exists (3.13+)


def _loop_sqrt(pool: _Pool) -> None:
    """One `math.sqrt(x)` per pool element."""
    for x in pool:
        _ = math.sqrt(x)


def _loop_cbrt(pool: _Pool) -> None:
    """One `math.cbrt(x)` per pool element."""
    for x in pool:
        _ = math.cbrt(x)


def _loop_exp(pool: _Pool) -> None:
    """One `math.exp(x)` per pool element."""
    for x in pool:
        _ = math.exp(x)


def _loop_exp2(pool: _Pool) -> None:
    """One `math.exp2(x)` per pool element."""
    for x in pool:
        _ = math.exp2(x)


def _loop_exp10(pool: _Pool) -> None:
    """One `10.0 ** x` per pool element."""
    for x in pool:
        _ = 10.0**x


def _loop_log(pool: _Pool) -> None:
    """One `math.log(x)` per pool element."""
    for x in pool:
        _ = math.log(x)


def _loop_log2(pool: _Pool) -> None:
    """One `math.log2(x)` per pool element."""
    for x in pool:
        _ = math.log2(x)


def _loop_log10(pool: _Pool) -> None:
    """One `math.log10(x)` per pool element."""
    for x in pool:
        _ = math.log10(x)


def _loop_pow(pool: _Pool) -> None:
    """One `x ** y` per pool element."""
    for x, y in pool:
        _ = x**y


def _loop_sin(pool: _Pool) -> None:
    """One `math.sin(x)` per pool element."""
    for x in pool:
        _ = math.sin(x)


def _loop_cos(pool: _Pool) -> None:
    """One `math.cos(x)` per pool element."""
    for x in pool:
        _ = math.cos(x)


def _loop_tan(pool: _Pool) -> None:
    """One `math.tan(x)` per pool element."""
    for x in pool:
        _ = math.tan(x)


def _loop_asin(pool: _Pool) -> None:
    """One `math.asin(x)` per pool element."""
    for x in pool:
        _ = math.asin(x)


def _loop_acos(pool: _Pool) -> None:
    """One `math.acos(x)` per pool element."""
    for x in pool:
        _ = math.acos(x)


def _loop_atan(pool: _Pool) -> None:
    """One `math.atan(x)` per pool element."""
    for x in pool:
        _ = math.atan(x)


def _loop_atan2(pool: _Pool) -> None:
    """One `math.atan2(x, y)` per pool element."""
    for x, y in pool:
        _ = math.atan2(x, y)


def _loop_hypot(pool: _Pool) -> None:
    """One `math.hypot(x, y)` per pool element."""
    for x, y in pool:
        _ = math.hypot(x, y)


def _loop_expm1(pool: _Pool) -> None:
    """One `math.expm1(x)` per pool element."""
    for x in pool:
        _ = math.expm1(x)


def _loop_log1p(pool: _Pool) -> None:
    """One `math.log1p(x)` per pool element."""
    for x in pool:
        _ = math.log1p(x)


def _loop_fmod(pool: _Pool) -> None:
    """One `math.fmod(x, y)` per pool element."""
    for x, y in pool:
        _ = math.fmod(x, y)


def _loop_remainder(pool: _Pool) -> None:
    """One `math.remainder(x, y)` per pool element."""
    for x, y in pool:
        _ = math.remainder(x, y)


def _loop_sinh(pool: _Pool) -> None:
    """One `math.sinh(x)` per pool element."""
    for x in pool:
        _ = math.sinh(x)


def _loop_cosh(pool: _Pool) -> None:
    """One `math.cosh(x)` per pool element."""
    for x in pool:
        _ = math.cosh(x)


def _loop_tanh(pool: _Pool) -> None:
    """One `math.tanh(x)` per pool element."""
    for x in pool:
        _ = math.tanh(x)


def _loop_asinh(pool: _Pool) -> None:
    """One `math.asinh(x)` per pool element."""
    for x in pool:
        _ = math.asinh(x)


def _loop_acosh(pool: _Pool) -> None:
    """One `math.acosh(x)` per pool element."""
    for x in pool:
        _ = math.acosh(x)


def _loop_atanh(pool: _Pool) -> None:
    """One `math.atanh(x)` per pool element."""
    for x in pool:
        _ = math.atanh(x)


def _loop_dist(pool: _Pool) -> None:
    """One `math.dist(p, q)` per pool element."""
    for p, q in pool:
        _ = math.dist(p, q)


def _loop_sumprod(pool: _Pool) -> None:
    """One `math.sumprod(p, q)` per pool element."""
    for p, q in pool:
        _ = math.sumprod(p, q)  # ty: ignore[unresolved-attribute] -- registered only where math.sumprod exists (3.12+)


def _loop_gamma(pool: _Pool) -> None:
    """One `math.gamma(x)` per pool element."""
    for x in pool:
        _ = math.gamma(x)


def _loop_lgamma(pool: _Pool) -> None:
    """One `math.lgamma(x)` per pool element."""
    for x in pool:
        _ = math.lgamma(x)


def _loop_erf(pool: _Pool) -> None:
    """One `math.erf(x)` per pool element."""
    for x in pool:
        _ = math.erf(x)


def _loop_erfc(pool: _Pool) -> None:
    """One `math.erfc(x)` per pool element."""
    for x in pool:
        _ = math.erfc(x)


# =================================================================================================
#  Loop registry
# =================================================================================================
@dataclass(frozen=True)
class FlopTypeLoopSpec:
    """One measurable flop type: its loop body, operand-pool factory, and display expression."""

    flop_type: FlopType
    expression: str
    loop: Callable[[_Pool], None]
    make_pool: Callable[[bool], _Pool]


def _all_loop_specs() -> list[FlopTypeLoopSpec]:
    """Every flop type with a standalone loop, in FlopType declaration order.

    Runtime availability (math.fma, math.sumprod) is not considered here -- the module-level
    registry split below handles it.
    """
    generic = (1.1, 2.9)  # positive, clear of every fold/strength-reduction trigger and domain edge
    open_unit = (-0.9, 0.9)  # strictly inside (-1, 1) for asin / acos / atanh
    return [
        FlopTypeLoopSpec(FlopType.ABS, "abs(x)", _loop_abs, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.MINUS, "-x", _loop_minus, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.COPYSIGN, "math.copysign(x, y)", _loop_copysign, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.COMP, "x <= y", _loop_comp, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.RND, "round(x, 0)", _loop_rnd, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.F2I, "int(x)", _loop_f2i, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.I2F, "CountedFloat(i) vs float(i)", _loop_i2f, _int_constructor_pool()),
        FlopTypeLoopSpec(FlopType.ADD, "x + y", _loop_add, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.SUB, "x - y", _loop_sub, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.MUL, "x * y", _loop_mul, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.DIV, "x / y", _loop_div, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.FMA, "math.fma(x, y, z)", _loop_fma, _triple_pool(*generic)),
        FlopTypeLoopSpec(FlopType.SQRT, "math.sqrt(x)", _loop_sqrt, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.CBRT, "math.cbrt(x)", _loop_cbrt, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.EXP, "math.exp(x)", _loop_exp, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.EXP2, "math.exp2(x)", _loop_exp2, _unary_pool(*generic)),
        # EXP10 has no direct math-module call; the constant-base fold of `10.0 ** x` is its one
        # counted spelling, so that is what the loop runs
        FlopTypeLoopSpec(FlopType.EXP10, "10.0 ** x", _loop_exp10, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.LOG, "math.log(x)", _loop_log, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.LOG2, "math.log2(x)", _loop_log2, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.LOG10, "math.log10(x)", _loop_log10, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.POW, "x ** y", _loop_pow, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.SIN, "math.sin(x)", _loop_sin, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.COS, "math.cos(x)", _loop_cos, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.TAN, "math.tan(x)", _loop_tan, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.ASIN, "math.asin(x)", _loop_asin, _unary_pool(*open_unit)),
        FlopTypeLoopSpec(FlopType.ACOS, "math.acos(x)", _loop_acos, _unary_pool(*open_unit)),
        FlopTypeLoopSpec(FlopType.ATAN, "math.atan(x)", _loop_atan, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.ATAN2, "math.atan2(x, y)", _loop_atan2, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.HYPOT, "math.hypot(x, y)", _loop_hypot, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.EXPM1, "math.expm1(x)", _loop_expm1, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.LOG1P, "math.log1p(x)", _loop_log1p, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.FMOD, "math.fmod(x, y)", _loop_fmod, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.REMAINDER, "math.remainder(x, y)", _loop_remainder, _pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.SINH, "math.sinh(x)", _loop_sinh, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.COSH, "math.cosh(x)", _loop_cosh, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.TANH, "math.tanh(x)", _loop_tanh, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.ASINH, "math.asinh(x)", _loop_asinh, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.ACOSH, "math.acosh(x)", _loop_acosh, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.ATANH, "math.atanh(x)", _loop_atanh, _unary_pool(*open_unit)),
        FlopTypeLoopSpec(FlopType.DIST, "math.dist(p, q)", _loop_dist, _point_pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.SUMPROD, "math.sumprod(p, q)", _loop_sumprod, _point_pair_pool(*generic)),
        FlopTypeLoopSpec(FlopType.GAMMA, "math.gamma(x)", _loop_gamma, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.LGAMMA, "math.lgamma(x)", _loop_lgamma, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.ERF, "math.erf(x)", _loop_erf, _unary_pool(*generic)),
        FlopTypeLoopSpec(FlopType.ERFC, "math.erfc(x)", _loop_erfc, _unary_pool(*generic)),
    ]


def _runtime_unavailable() -> dict[FlopType, str]:
    """The types whose measuring spelling this Python does not provide."""
    unavailable: dict[FlopType, str] = {}
    if not hasattr(math, "fma"):
        unavailable[FlopType.FMA] = "math.fma is unavailable on this Python (added in 3.13)"
    if not hasattr(math, "sumprod"):
        unavailable[FlopType.SUMPROD] = "math.sumprod is unavailable on this Python (added in 3.12)"
    return unavailable


def excluded_flop_types() -> dict[FlopType, str]:
    """The flop types without a per-type overhead row, each mapped to its measurement reason.

    Exclusion rule: a type is excluded only when its standalone measurement is unreliable or
    impossible, never because its result would be unflattering -- every entry states its reason,
    and the printed report shows this mapping so exemptions are visible in every capture.

    Returns a fresh dict per call: construction is trivial, and callers never share a mutable.
    """
    return {
        FlopType.HYPOT_XARG: "cost increment per hypot() argument beyond two; not a standalone operation",
        FlopType.DIST_XARG: "cost increment per dist() dimension beyond two; not a standalone operation",
        FlopType.SUMPROD_XELEM: "cost increment per sumprod() element beyond two; not a standalone operation",
        **_runtime_unavailable(),
    }


def per_flop_type_specs() -> list[FlopTypeLoopSpec]:
    """Every measurable flop type's loop spec, in FlopType declaration order.

    A plain function rather than a module-level constant -- like excluded_flop_types(), and
    returning a fresh list per call for the same reason -- so the registry builders execute inside
    the tests that pin them: mutation testing attributes tests to a function only when it runs
    during one, and import-time construction is invisible to that attribution.
    """
    excluded = excluded_flop_types()
    return [spec for spec in _all_loop_specs() if spec.flop_type not in excluded]


# =================================================================================================
#  The timed loop
# =================================================================================================
class PerFlopTypeLoop(MicroBenchmark):
    """Times one per-type loop over its operand pool, optionally inside a FlopCountingContext.

    Each timed run makes n_executions passes over the pool. The counted variant enters the
    context inside the timed region, where its fixed patch/unpatch cost amortizes over the
    run's target duration.
    """

    def __init__(self, name: str, loop: Callable[[_Pool], None], pool: _Pool, in_counting_context: bool) -> None:
        """Create the timed loop; in_counting_context selects the counted variant's context."""
        super().__init__(name=name, single_execution="pass")
        self._loop = loop
        self._pool = pool
        self._in_counting_context = in_counting_context
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int) -> None:
        """Store the pass count for the next timed run."""
        self._n_executions = n_executions

    def _run_benchmark(self) -> None:
        """Run n_executions passes over the pool."""
        if self._in_counting_context:
            with FlopCountingContext():
                for _ in range(self._n_executions):
                    self._loop(self._pool)
        else:
            for _ in range(self._n_executions):
                self._loop(self._pool)
