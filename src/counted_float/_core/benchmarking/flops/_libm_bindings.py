"""ctypes bindings to the C math library, for the benchmark probes that need the bare call.

numba compiles a ctypes function into a plain indirect call -- the same loop shape as the
libm-backed probes it compiles directly, plus one integer-side pointer reload per iteration --
and without numba the ctypes function is just as callable from the pure-Python fallback path.
On Windows the C99 math functions live in the UCRT rather than a separate libm.

Admission criterion -- a probe goes through a ctypes binding only where numba's own route to
the function either does not exist (`math.remainder` has no numba implementation) or inserts
wrapper code around the libm call that CPython's own call never executes (`np.cbrt` adds
NaN/sign handling; CPython's `math.cbrt` calls libm directly).  Everywhere else the
numba-compiled call already is the bare libm call or instruction, and switching it to ctypes
would only add the per-iteration pointer reload.
"""

import ctypes
import ctypes.util
import sys
from collections.abc import Callable


def _load_libm() -> ctypes.CDLL:
    """Load the C math library (the UCRT on Windows, libm elsewhere)."""
    return ctypes.CDLL("ucrtbase" if sys.platform == "win32" else ctypes.util.find_library("m"))


_libm = _load_libm()


def libm_cbrt() -> Callable[[float], float]:
    """The C99 ``double cbrt(double)`` function, as a ctypes function object."""
    fn = _libm.cbrt
    fn.restype = ctypes.c_double
    fn.argtypes = [ctypes.c_double]
    return fn


def libm_remainder() -> Callable[[float, float], float]:
    """The C99 ``double remainder(double, double)`` function, as a ctypes function object."""
    fn = _libm.remainder
    fn.restype = ctypes.c_double
    fn.argtypes = [ctypes.c_double, ctypes.c_double]
    return fn
