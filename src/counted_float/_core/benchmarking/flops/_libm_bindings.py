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


def _load_libm() -> ctypes.CDLL | None:
    """Load the C math library (the UCRT on Windows, libm elsewhere), or None if unlocatable.

    ``ctypes.util.find_library`` needs ldconfig-style machinery that platforms like musl or
    Android may lack; returning None instead of crashing defers the failure to the getters
    below, which raise a clear error at flops-benchmark time rather than at import time.
    """
    name = "ucrtbase" if sys.platform == "win32" else ctypes.util.find_library("m")
    if name is None:
        return None
    try:
        return ctypes.CDLL(name)
    except OSError:
        return None


_libm = _load_libm()


def _require_libm() -> ctypes.CDLL:
    """The loaded C math library, or a clear error naming the feature that needs it."""
    if _libm is None:
        raise RuntimeError(
            "the flops benchmark needs the C math library for its cbrt/remainder probes, "
            "and none could be located on this platform"
        )
    return _libm


def libm_cbrt() -> Callable[[float], float]:
    """The C99 ``double cbrt(double)`` function, as a ctypes function object."""
    fn = _require_libm().cbrt
    fn.restype = ctypes.c_double
    fn.argtypes = [ctypes.c_double]
    return fn


def libm_remainder() -> Callable[[float, float], float]:
    """The C99 ``double remainder(double, double)`` function, as a ctypes function object."""
    fn = _require_libm().remainder
    fn.restype = ctypes.c_double
    fn.argtypes = [ctypes.c_double, ctypes.c_double]
    return fn
