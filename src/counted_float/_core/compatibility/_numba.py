from collections.abc import Callable
from typing import TypeVar, overload

from ._optional_dependencies import is_importable

_ProbeFn = TypeVar("_ProbeFn", bound=Callable[..., object])

if is_importable("numba"):
    import numba  # ty: ignore[unresolved-import] -- numba is an optional dependency; shimmed below if absent
else:
    # dummy decorator replacing numba.jit / numba.njit: identity in both call forms, so that
    # without numba the decorated probe keeps its original callable type rather than `object`
    @overload
    def dummy_decorator(func: _ProbeFn, /) -> _ProbeFn: ...
    @overload
    def dummy_decorator(*args: object, **kwargs: object) -> Callable[[_ProbeFn], _ProbeFn]: ...
    def dummy_decorator(*args: object, **kwargs: object) -> object:
        # does nothing and can be used with or without arguments
        if len(args) == 1 and isinstance(args[0], Callable):
            # decorator used without arguments
            return args[0]

        # decorator used with arguments
        def decorator(func: Callable[..., object]) -> Callable[..., object]:
            return func

        return decorator

    # create a dummy numba object with numba.jit and numba.njit dummy decorators
    class Numba:
        __version__ = "0.0.0"
        jit = dummy_decorator
        njit = dummy_decorator

    numba = Numba  # ty: ignore[invalid-assignment] -- module-shaped stand-in for the absent optional module


def is_numba_importable() -> bool:
    """Whether the real numba is in use, as opposed to the identity-decorator shim above."""
    return is_importable("numba")
