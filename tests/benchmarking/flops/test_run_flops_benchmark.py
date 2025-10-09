from counted_float._core.benchmarking import run_flops_benchmark


def test_run_flops_benchmark():
    # simple test to see if no exceptions are raised
    result = run_flops_benchmark(n_seconds_per_run_target=1e-4)
    result.show()
