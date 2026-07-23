import pytest

from counted_float._core.compatibility import is_numba_installed, numba


# =================================================================================================
#  is_numba_installed
# =================================================================================================
def test_is_numba_installed():
    # --- arrange -----------------------------------------
    is_numba_truly_installed = hasattr(numba, "double")

    # --- act ---------------------------------------------
    is_numba_deemed_installed = is_numba_installed()

    # --- assert ------------------------------------------
    assert is_numba_deemed_installed == is_numba_truly_installed


@pytest.mark.skipif(is_numba_installed(), reason="the dummy decorator shim exists only when numba is absent")
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
