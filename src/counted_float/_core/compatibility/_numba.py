from collections.abc import Callable

try:
    import numba  # ty: ignore[unresolved-import] -- numba is an optional dependency; shimmed below if absent

    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

    # dummy decorator that will replace numba.jit and numba.njit
    def dummy_decorator(*args: object, **kwargs: object) -> Callable:
        # dummy decorator that does nothing and can be used with or without arguments
        if len(args) == 1 and isinstance(args[0], Callable):
            # decorator used without arguments
            return args[0]

        # decorator used with arguments
        def decorator(func: Callable) -> Callable:
            return func

        return decorator

    # create a dummy numba object with numba.jit and numba.njit dummy decorators
    class Numba:
        __version__ = "0.0.0"
        jit = dummy_decorator
        njit = dummy_decorator

    numba = Numba  # ty: ignore[invalid-assignment] -- module-shaped stand-in for the absent optional module


def is_numba_installed() -> bool:
    return NUMBA_AVAILABLE
