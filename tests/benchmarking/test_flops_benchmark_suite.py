import pytest

from counted_float._core.benchmarking._flops_benchmark_suite import FlopsBenchmarkSuite
from counted_float._core.benchmarking._flops_micro_benchmark import FlopsMicroBenchmark
from counted_float._core.counting.models import FlopsBenchmarkResults, FlopType


@pytest.mark.requires_benchmarking_deps
def test_flops_benchmarking_suite_get():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    benchmarks = suite.get_flops_benchmarking_suite(size=12345)

    # --- assert ------------------------------------------
    assert None in benchmarks.keys()
    assert all([ft in benchmarks.keys() for ft in FlopType])
    assert all([isinstance(v, FlopsMicroBenchmark) for v in benchmarks.values()])
    assert all([v.size == 12345 for v in benchmarks.values()])


@pytest.mark.requires_benchmarking_deps
def test_flops_benchmarking_suite_run():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    result = suite.run(
        array_size=10,
        n_runs_total=10,
        n_runs_warmup=5,
        n_seconds_per_run_target=0.001,
    )  # override defaults to keep test short

    # --- assert ------------------------------------------
    assert isinstance(result, FlopsBenchmarkResults)
