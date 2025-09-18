from importlib.metadata import version

from counted_float._core.models import FlopsBenchmarkResults

from ._flops_benchmark_suite import FlopsBenchmarkSuite


def run_flops_benchmark() -> FlopsBenchmarkResults:
    """Run the flops benchmark suite with default settings returns a FlopsBenchmarkResults object."""

    print()
    print(f"Running FLOPS benchmarks using counted-float {version('counted-float')} ...")
    print()

    benchmark_results = FlopsBenchmarkSuite().run()

    print()

    return benchmark_results
