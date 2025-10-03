from importlib.metadata import version

from .flops_v2 import FlopsBenchmarkResults_V2, FlopsBenchmarkSuite_V2


def run_flops_benchmark() -> FlopsBenchmarkResults_V2:
    """Run the flops benchmark suite with default settings returns a FlopsBenchmarkResults object."""

    print()
    print(f"Running FLOPS benchmarks using counted-float {version('counted-float')} ...")
    print()

    benchmark_results = FlopsBenchmarkSuite_V2().run()

    print()

    return benchmark_results
