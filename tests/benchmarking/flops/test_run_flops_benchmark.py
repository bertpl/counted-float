from counted_float._core.benchmarking import run_flops_benchmark


def test_run_flops_benchmark():
    # simple test to see if no exceptions are raised
    result = run_flops_benchmark(t_slice_target_ms=0.1, n_rounds_measure=5, n_rounds_warmup=1, seed=42)
    result.show()
