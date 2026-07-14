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


def test_run_flops_benchmark_warns_when_cpu_freq_unavailable(monkeypatch):
    """A missing CPU-frequency reading is surfaced as a RuntimeWarning, even with progress silenced."""

    # --- arrange ----------------------
    monkeypatch.setattr(_flops_benchmark_suite, "get_cpu_frequency_mhz_current", lambda: None)

    # --- act / assert -----------------
    with pytest.warns(RuntimeWarning, match="frequency is unavailable"):
        run_flops_benchmark(t_slice_target_ms=0.1, n_rounds_measure=5, n_rounds_warmup=1, seed=42, verbose=False)


def test_run_flops_benchmark_no_freq_warning_when_available(monkeypatch, recwarn):
    """When the CPU frequency reads back, no nanoseconds/frequency warning is emitted."""

    # --- arrange ----------------------
    monkeypatch.setattr(_flops_benchmark_suite, "get_cpu_frequency_mhz_current", lambda: 3000.0)

    # --- act --------------------------
    run_flops_benchmark(t_slice_target_ms=0.1, n_rounds_measure=5, n_rounds_warmup=1, seed=42, verbose=False)

    # --- assert -----------------------
    assert not [w for w in recwarn if issubclass(w.category, RuntimeWarning) and "frequency" in str(w.message)]
