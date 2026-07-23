import subprocess
import sys

import pytest

from counted_float._core.benchmarking.flops import _libm_bindings


def test_importing_the_benchmarking_api_does_not_load_libm():
    """The libm ctypes load must stay confined to running the flops benchmark.

    On platforms without a locatable C math library (musl, Android) the load fails; that
    failure must not break `import counted_float.benchmarking`, whose other entry point
    (run_counted_float_benchmark) never touches libm. Run in a fresh interpreter so the
    check is independent of what this test session already imported.
    """
    code = (
        "import sys; import counted_float; import counted_float.benchmarking; "
        "assert 'counted_float._core.benchmarking.flops._libm_bindings' not in sys.modules, "
        "'importing the benchmarking API must not bind libm'"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603 -- fixed interpreter, literal code


@pytest.mark.parametrize("getter", [_libm_bindings.libm_cbrt, _libm_bindings.libm_remainder])
def test_getters_raise_a_clear_error_when_libm_is_unlocatable(monkeypatch, getter):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(_libm_bindings, "_libm", None)  # what _load_libm returns on musl/Android

    # --- act / assert ------------------------------------
    with pytest.raises(RuntimeError, match="C math library"):
        getter()


def test_load_libm_survives_an_unlocatable_library(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(_libm_bindings.ctypes.util, "find_library", lambda name: None)

    # --- act / assert ------------------------------------
    assert _libm_bindings._load_libm() is None or sys.platform == "win32"
