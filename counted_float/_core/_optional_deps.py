"""
Module implementing boolean flags indicating whether optional dependencies are available & decorators to
safeguard execution of functions that require these dependencies.
"""

import functools
from typing import Callable

# -------------------------------------------------------------------------
#  Flags
# -------------------------------------------------------------------------
try:
    import numba
    import numpy
    import psutil

    FLAG_BENCHMARK_DEPS = True
except ImportError:
    FLAG_BENCHMARK_DEPS = False


# -------------------------------------------------------------------------
#  Decorators
# -------------------------------------------------------------------------
def requires_benchmark_deps(fun: Callable) -> Callable:
    """
    Decorator to mark a function that requires some deps to be installed.

    USAGE:

        @requires_benchmark_deps
        def fun_that_needs_numba_or_numpy_or_psutil():
            pass

    This will ensure that the function - when it is called for the first time - will check if the required
    dependencies are available.  If not, an ImportError will be raised with an informative message.
    """

    @functools.wraps(fun)
    def wrapped_fun(*args, **kwargs):
        if not FLAG_BENCHMARK_DEPS:
            raise ImportError(
                "This function requires counted_float to be installed with benchmark optional dependencies. "
                + "Please install this package as counted_float[benchmark]."
            )
        else:
            return fun(*args, **kwargs)

    return wrapped_fun
