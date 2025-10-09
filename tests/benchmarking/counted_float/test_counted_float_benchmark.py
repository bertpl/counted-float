from counted_float._core.benchmarking import run_counted_float_benchmark


def test_run_counted_float_benchmark():
    # Rudimentary test to check the benchmark runs without errors
    result = run_counted_float_benchmark(t_target_sec=0.001)
    result.show()
