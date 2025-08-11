import pytest

from counted_float._core.benchmarking._flops_micro_benchmark import FlopsMicroBenchmark
from counted_float._core.benchmarking._models import MicroBenchmarkResult, SingleRunResult


@pytest.mark.requires_benchmarking_deps
def test_flops_micro_benchmark():
    # --- arrange -----------------------------------------
    import numpy as np

    def test_function(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
        for i in range(n):
            out_f[i] = (2 * in_f1[i]) + in_f2[i]

    benchmark = FlopsMicroBenchmark(name="test", f=test_function, size=1234)

    # --- act ---------------------------------------------
    single_run_result = benchmark.run_once(n_operations=10)
    multi_run_result = benchmark.run_many(n_runs_total=10, n_runs_warmup=2, n_seconds_per_run_target=0.01)

    # --- assert ------------------------------------------
    assert isinstance(single_run_result, SingleRunResult)
    assert isinstance(multi_run_result, MicroBenchmarkResult)
