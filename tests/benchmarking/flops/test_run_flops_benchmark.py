import pytest

from counted_float._core.benchmarking import run_flops_benchmark
from counted_float._core.benchmarking.flops import _flops_benchmark_suite


def test_run_flops_benchmark():
    # simple test to see if no exceptions are raised
    result = run_flops_benchmark(t_slice_target_ms=0.1, n_rounds_measure=5, n_rounds_warmup=1, seed=42)
    result.show()


def test_run_flops_benchmark_verbose_false_is_silent(capsys):
    # --- act --------------------------
    run_flops_benchmark(t_slice_target_ms=0.1, n_rounds_measure=5, n_rounds_warmup=1, seed=42, verbose=False)

    # --- assert -----------------------
    assert capsys.readouterr().out == ""


def test_run_flops_benchmark_warns_when_numba_missing(monkeypatch):
    """The missing-numba notice is a RuntimeWarning and fires even with progress silenced."""

    # --- arrange ----------------------
    monkeypatch.setattr(_flops_benchmark_suite, "is_numba_installed", lambda: False)

    # --- act / assert -----------------
    with pytest.warns(RuntimeWarning, match="numba"):
        run_flops_benchmark(t_slice_target_ms=0.1, n_rounds_measure=5, n_rounds_warmup=1, seed=42, verbose=False)
