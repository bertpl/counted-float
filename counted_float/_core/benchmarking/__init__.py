from importlib.metadata import version

from .flops_v1 import FlopsBenchmarkResults_V1, FlopsBenchmarkSuite_V1


def run_flops_benchmark() -> FlopsBenchmarkResults_V1:
    """Run the flops benchmark suite with default settings returns a FlopsBenchmarkResults object."""

    print()
    print(f"Running FLOPS benchmarks using counted-float {version('counted-float')} ...")
    print()

    benchmark_results = FlopsBenchmarkSuite_V1().run()

    print()

    return benchmark_results
