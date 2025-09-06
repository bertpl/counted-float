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
