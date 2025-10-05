from .flops import FlopsBenchmarkResults_V2, FlopsBenchmarkSuite


def run_flops_benchmark() -> FlopsBenchmarkResults_V2:
    """Run the flops benchmark suite with default settings returns a FlopsBenchmarkResults object."""

    benchmark_results = FlopsBenchmarkSuite().run()

    print()

    return benchmark_results
