from typing import TYPE_CHECKING

from counted_float import BuiltInData

if TYPE_CHECKING:
    from counted_float._core.models import FlopsBenchmarkResults


def test_flops_benchmark_results_show():
    """Minimal test to check if MyBaseModel.show() at least does not raise exceptions."""

    # --- arrange -----------------------------------------
    flops_benchmark_results: FlopsBenchmarkResults = list(BuiltInData.benchmarks().values()).pop()

    # --- act ---------------------------------------------
    str(flops_benchmark_results)
    repr(flops_benchmark_results)
    flops_benchmark_results.show()
