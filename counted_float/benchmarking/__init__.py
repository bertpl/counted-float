from counted_float._core._optional_deps import FLAG_BENCHMARK_DEPS

__all__ = []

if FLAG_BENCHMARK_DEPS:
    from counted_float._core.benchmarking import FlopsBenchmarkResults, run_flops_benchmark

    __all__ = [
        "FlopsBenchmarkResults",
        "run_flops_benchmark",
    ]

# delete variable again, we don't want to expose this
del FLAG_BENCHMARK_DEPS
