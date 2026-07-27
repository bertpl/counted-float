"""The building blocks of the sumprod probes: CPython's TripleLength algorithm, ported to numba.

CPython's ``math.sumprod`` runs a compensated (extended-precision) accumulation on exact-float
inputs (mathmodule.c, the fma-reliable build): per element a ``dl_mul`` error-free product --
hi = x*y, lo = fma(x, y, -hi) -- folded into a three-double running total (``tl_fma``), with the
``tl_to_d`` close-out collapsing that total to one double.  The helpers here mirror CPython's
functions one-to-one and are inlined at the numba-IR level (inline="always"), so a probe calling
them compiles to a single straight-line loop body -- no call overhead inside the timed loop.

The error terms need a genuine fused multiply-add, which numba cannot spell: it has no
``math.fma``, and the contract-scoped fastmath mechanism the FMA probes use cannot express
``fma(x, y, -x*y)`` -- LLVM CSEs the two multiplies into one value with two uses, which blocks
contraction and turns the error term into a computed zero.  Declaring the LLVM intrinsic
directly emits the fused instruction inline, with no fastmath flags involved, so contraction
stays scoped to the FMA probes.

Without numba the probes run as plain Python, so the fma degrades to ``math.fma`` where it
exists (Python 3.13+) and to the double-rounded ``x * y + z`` before that -- acceptable only
because the no-numba fallback path already warns that its results are unusable.
"""

import math
from collections.abc import Callable

from counted_float._core.compatibility import is_importable, numba


def _make_fma_single() -> Callable[[float, float, float], float]:
    """Build the fused multiply-add usable inside (or, without numba, instead of) an njit probe."""
    if not is_importable("numba"):
        if hasattr(math, "fma"):
            return math.fma
        return lambda x, y, z: x * y + z

    from llvmlite import ir  # ty: ignore[unresolved-import] -- ships with the optional numba dependency
    from numba.core import types  # ty: ignore[unresolved-import] -- numba is an optional dependency
    from numba.extending import intrinsic  # ty: ignore[unresolved-import] -- numba is an optional dependency

    @intrinsic
    def fma_intrinsic(typingctx: object, x: object, y: object, z: object) -> object:
        sig = types.float64(types.float64, types.float64, types.float64)

        def codegen(context: object, builder: ir.IRBuilder, signature: object, args: tuple[object, ...]) -> object:
            fnty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()] * 3)
            fn = builder.module.declare_intrinsic("llvm.fma", [ir.DoubleType()], fnty)
            return builder.call(fn, args)

        return sig, codegen

    # an @intrinsic object is only callable from numba-compiled code; the declared signature is
    # the plain-Python contract the fallbacks above satisfy
    return fma_intrinsic  # ty: ignore[invalid-return-type]


_fma_single = _make_fma_single()


@numba.njit(inline="always")
def _dl_sum(a: float, b: float) -> tuple[float, float]:
    # error-free transformation of a + b into (hi, lo)
    x = a + b
    z = x - a
    y = (a - (x - z)) + (b - z)
    return x, y


@numba.njit(inline="always")
def tl_fma(x: float, y: float, hi: float, lo: float, tiny: float) -> tuple[float, float, float]:
    """Fold the compensated product x*y into the (hi, lo, tiny) running total."""
    ph = x * y
    pl = _fma_single(x, y, -ph)
    smx, smy = _dl_sum(hi, ph)
    r1x, r1y = _dl_sum(lo, pl)
    r2x, r2y = _dl_sum(r1x, smy)
    return smx, r2x, tiny + (r1y + r2y)


@numba.njit(inline="always")
def tl_to_d(hi: float, lo: float, tiny: float) -> float:
    """Collapse the three-double total to one double."""
    lastx, lasty = _dl_sum(lo, hi)
    return tiny + lasty + lastx
