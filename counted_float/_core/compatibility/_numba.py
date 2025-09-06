from collections.abc import Callable

try:
    import numba


except ImportError:
    # dummy decorator that will replace numba.jit and numba.njit
    def dummy_decorator(*args, **kwargs):
        # dummy decorator that does nothing and can be used with or without arguments
        if len(args) == 1 and isinstance(args[0], Callable):
            # decorator used without arguments
            return args[0]
        else:
            # decorator used with arguments
            def decorator(func):
                return func

            return decorator

    # create a dummy numba object with numba.jit and numba.njit dummy decorators
    class Numba:
        __version__ = "0.0.0"
        jit = dummy_decorator
        njit = dummy_decorator

    numba = Numba


def is_numba_installed() -> bool:
    return numba.__version__ != "0.0.0"
