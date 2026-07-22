"""A numba intrinsic emitting the ``llvm.fma.f64`` instruction, for the sumprod probes.

The sumprod probes port CPython's extended-precision accumulation, whose error terms are
computed as ``fma(x, y, -x*y)``.  numba has no ``math.fma``, and the contract-scoped fastmath
mechanism the FMA probes use cannot express this shape: LLVM CSEs the two ``x*y`` into one
multiply with two uses, which blocks contraction and turns the error term into a computed zero.
Declaring the LLVM intrinsic directly emits the fused instruction inline -- no fastmath flags
involved, so contraction stays scoped to the FMA probes.

Without numba the probes run as plain Python, so ``fma_single`` degrades to ``math.fma`` where
it exists (Python 3.13+) and to the double-rounded ``x * y + z`` before that -- acceptable only
because the no-numba fallback path already warns that its results are unusable.
"""

import math
from collections.abc import Callable

from counted_float._core.compatibility import is_numba_installed


def _make_fma_single() -> Callable[[float, float, float], float]:
    """Build the fused multiply-add usable inside (or, without numba, instead of) an njit probe."""
    if not is_numba_installed():
        if hasattr(math, "fma"):
            return math.fma
        return lambda x, y, z: x * y + z

    from llvmlite import ir  # ty: ignore[unresolved-import] -- ships with the optional numba dependency
    from numba.core import types  # ty: ignore[unresolved-import] -- numba is an optional dependency
    from numba.extending import intrinsic  # ty: ignore[unresolved-import] -- numba is an optional dependency

    @intrinsic
    def fma_intrinsic(typingctx: object, x: object, y: object, z: object) -> object:
        sig = types.float64(types.float64, types.float64, types.float64)

        def codegen(context: object, builder: ir.IRBuilder, signature: object, args: tuple) -> object:
            fnty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType()] * 3)
            fn = builder.module.declare_intrinsic("llvm.fma", [ir.DoubleType()], fnty)
            return builder.call(fn, args)

        return sig, codegen

    # an @intrinsic object is only callable from numba-compiled code; the declared signature is
    # the plain-Python contract the fallbacks above satisfy
    return fma_intrinsic  # ty: ignore[invalid-return-type]


fma_single = _make_fma_single()
