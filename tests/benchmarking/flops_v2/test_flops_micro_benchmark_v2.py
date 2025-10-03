import pytest

from counted_float._core.benchmarking.flops_v2 import FlopsMicroBenchmark_V2
from counted_float._core.benchmarking.flops_v2._array_generator import ArrayGenerator
from counted_float._core.models import MicroBenchmarkResult, SingleRunResult


def test_flops_micro_benchmark_v2():
    # --- arrange -----------------------------------------
    import numpy as np

    def test_function(n_executions: int, size: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
        for _ in range(n_executions):
            for i in range(size):
                out_f[i] = 2 * in_f[i]

    benchmark = FlopsMicroBenchmark_V2(
        name="test", f=test_function, size=1234, array_init=ArrayGenerator.lin_range(0.9, 1.1)
    )

    # --- act ---------------------------------------------
    single_run_result = benchmark.run_once(n_executions=10)
    multi_run_result = benchmark.run_many(n_runs_total=10, n_runs_warmup=2, n_seconds_per_run_target=0.01)

    # --- assert ------------------------------------------
    assert isinstance(single_run_result, SingleRunResult)
    assert isinstance(multi_run_result, MicroBenchmarkResult)
