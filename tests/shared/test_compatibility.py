from counted_float._core.compatibility import is_importable, numba
from tests._capabilities import needs_no_numba


# =================================================================================================
#  is_importable
# =================================================================================================
def test_is_importable_agrees_with_the_shim_that_is_in_place():
    # --- arrange -----------------------------------------
    is_numba_truly_installed = hasattr(numba, "double")

    # --- act ---------------------------------------------
    is_numba_deemed_installed = is_importable("numba")

    # --- assert ------------------------------------------
    assert is_numba_deemed_installed == is_numba_truly_installed


@needs_no_numba
def test_numba_dummy_decorator_bare_form_returns_the_function():
    # without numba, `@njit` used bare (no parentheses) must return the decorated function unchanged
    # --- arrange -----------------------------------------
    from counted_float._core.compatibility._numba import dummy_decorator

    def probe():
        return 1.0

    # --- act ---------------------------------------------
    decorated = dummy_decorator(probe)

    # --- assert ------------------------------------------
    assert decorated is probe


@needs_no_numba
def test_numba_dummy_decorator_parametrized_form_calls_through():
    # without numba, `@njit(cache=True)` (the parametrized inner-decorator path, distinct from the
    # bare form) must return a decorator that yields a function which still calls through unchanged
    # --- arrange -----------------------------------------
    from counted_float._core.compatibility._numba import dummy_decorator

    def probe(x):
        return x + 1.0

    # --- act ---------------------------------------------
    decorated = dummy_decorator(cache=True)(probe)

    # --- assert ------------------------------------------
    assert decorated is probe
    assert decorated(2.0) == 3.0


@needs_no_numba
def test_numba_dummy_decorator_signature_string_form_returns_a_working_decorator():
    # without numba, `njit('float64(float64)')` -- a single non-callable positional arg -- must take
    # the `isinstance(args[0], Callable)` false branch and return a decorator, not the string itself
    # --- arrange -----------------------------------------
    from counted_float._core.compatibility._numba import dummy_decorator

    def probe(x):
        return x * 2.0

    # --- act ---------------------------------------------
    decorator = dummy_decorator("float64(float64)")

    # --- assert ------------------------------------------
    assert callable(decorator)
    decorated = decorator(probe)
    assert decorated is probe
    assert decorated(3.0) == 6.0
