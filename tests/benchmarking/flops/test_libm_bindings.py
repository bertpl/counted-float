import ctypes
import math
import subprocess
import sys

import pytest

from counted_float._core.benchmarking.flops import libm_bindings

# The real-result probes below need a locatable C math library; skip on platforms (musl, Android)
# where find_library cannot resolve one, matching how the getters themselves degrade.
_needs_libm = pytest.mark.skipif(
    libm_bindings._load_libm() is None, reason="no locatable C math library on this platform"
)


def test_importing_the_benchmarking_api_does_not_load_libm():
    """The libm ctypes load must stay confined to running the flops benchmark.

    On platforms without a locatable C math library (musl, Android) the load fails; that
    failure must not break `import counted_float.benchmarking`, whose other entry point
    (run_counted_float_benchmark) never touches libm. Run in a fresh interpreter so the
    check is independent of what this test session already imported.
    """
    code = (
        "import sys; import counted_float; import counted_float.benchmarking; "
        "assert 'counted_float._core.benchmarking.flops.libm_bindings' not in sys.modules, "
        "'importing the benchmarking API must not bind libm'"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603 -- fixed interpreter, literal code


@pytest.mark.parametrize("getter", [libm_bindings.libm_cbrt, libm_bindings.libm_remainder])
def test_getters_raise_a_clear_error_when_libm_is_unlocatable(monkeypatch, getter):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(libm_bindings, "_load_libm", lambda: None)  # musl/Android: no locatable libm

    # --- act / assert ------------------------------------
    with pytest.raises(RuntimeError, match="C math library"):
        getter()


def test_load_libm_survives_an_unlocatable_library(monkeypatch):
    # --- arrange -----------------------------------------
    # find_library returning None is the musl/Android case; clear the cache so this call re-runs
    # the loader rather than returning a real library some earlier test cached
    monkeypatch.setattr(libm_bindings.ctypes.util, "find_library", lambda name: None)
    libm_bindings._load_libm.cache_clear()

    # --- act / assert ------------------------------------
    try:
        assert libm_bindings._load_libm() is None or sys.platform == "win32"
    finally:
        libm_bindings._load_libm.cache_clear()  # drop the None so later real calls reload


def test_load_libm_returns_none_when_the_library_fails_to_load(monkeypatch):
    # find_library locates a name but the CDLL load raises OSError -> None, deferring to the clear
    # RuntimeError _require_libm raises at flops-benchmark time
    # --- arrange -----------------------------------------
    def _raise_oserror(*_args, **_kwargs):
        raise OSError("simulated libm load failure")

    monkeypatch.setattr(ctypes, "CDLL", _raise_oserror)
    libm_bindings._load_libm.cache_clear()

    # --- act / assert ------------------------------------
    try:
        assert libm_bindings._load_libm() is None
    finally:
        libm_bindings._load_libm.cache_clear()  # drop the None so later real calls reload


@_needs_libm
@pytest.mark.parametrize(
    ("value", "expected"),
    [(8.0, 2.0), (27.0, 3.0), (-8.0, -2.0), (1.0, 1.0), (0.0, 0.0)],
)
def test_libm_cbrt_computes_real_cube_roots(value: float, expected: float):
    # a wrong restype/argtypes (ctypes defaults restype to c_int) would corrupt the returned double
    # --- arrange -----------------------------------------
    cbrt = libm_bindings.libm_cbrt()

    # --- act ---------------------------------------------
    result = cbrt(value)

    # --- assert ------------------------------------------
    # approx, not exact: cbrt's last bit is platform-dependent (glibc returns 3.0000000000000004 for
    # 27.0); a corrupted restype/argtypes would be off by orders of magnitude, not one ULP
    assert result == pytest.approx(expected)


@_needs_libm
@pytest.mark.parametrize(("x", "y"), [(5.0, 3.0), (7.5, 2.0), (-5.0, 3.0), (10.0, 4.0), (1.0, 3.0)])
def test_libm_remainder_matches_math_remainder(x: float, y: float):
    # a wrong restype/argtypes would corrupt the result; math.remainder is the same IEEE operation
    # --- arrange -----------------------------------------
    remainder = libm_bindings.libm_remainder()

    # --- act ---------------------------------------------
    result = remainder(x, y)

    # --- assert ------------------------------------------
    assert result == math.remainder(x, y)
