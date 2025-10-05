from .flops import FlopsBenchmarkResults, FlopsBenchmarkSuite


def run_flops_benchmark() -> FlopsBenchmarkResults:
    """Run the flops benchmark suite with default settings returns a FlopsBenchmarkResults object."""

    benchmark_results = FlopsBenchmarkSuite().run()

    print()

    return benchmark_results
