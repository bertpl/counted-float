from counted_float._core.benchmarking.flops_v1 import FlopsBenchmarkSuite_V1, FlopsMicroBenchmark_V1
from counted_float._core.models import FlopsBenchmarkResults_V1, FlopType


def test_flops_benchmarking_suite_get():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite_V1()

    # --- act ---------------------------------------------
    benchmarks = suite.get_flops_benchmarking_suite(size=12345)

    # --- assert ------------------------------------------
    assert None in benchmarks.keys()
    assert all([ft in benchmarks.keys() for ft in FlopType])
    assert all([isinstance(v, FlopsMicroBenchmark_V1) for v in benchmarks.values()])
    assert all([v.size == 12345 for v in benchmarks.values()])


def test_flops_benchmarking_suite_run():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite_V1()

    # --- act ---------------------------------------------
    result = suite.run(
        array_size=10,
        n_runs_total=10,
        n_runs_warmup=5,
        n_seconds_per_run_target=0.001,
    )  # override defaults to keep test short

    # --- assert ------------------------------------------
    assert isinstance(result, FlopsBenchmarkResults_V1)
