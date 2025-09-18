from counted_float import BuiltInData, FlopsBenchmarkResults


def test_flops_benchmark_results_show():
    """Minimal test to check if MyBaseModel.show() at least does not raise exceptions."""

    # --- arrange -----------------------------------------
    flops_benchmark_results: FlopsBenchmarkResults = list(BuiltInData.benchmarks().values()).pop()

    # --- act ---------------------------------------------
    flops_benchmark_results.show()
