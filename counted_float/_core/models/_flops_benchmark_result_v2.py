from __future__ import annotations

from ._base import MyBaseModel
from ._flop_type import FlopType
from ._flop_weights import FlopWeights
from ._flops_benchmark_meta_data import BenchmarkSettings, SystemInfo
from ._flops_benchmark_type import FlopsBenchmarkType
from ._micro_benchmark_result import Quantiles


# =================================================================================================
#  Main Flops Benchmark Information
# =================================================================================================
class FlopsBenchmarkResults_V2(MyBaseModel):
    system: SystemInfo
    benchmark_settings: BenchmarkSettings
    n_cycles_per_op: dict[FlopsBenchmarkType, Quantiles]  # number of cpu cycles per element in array

    def flop_weights(self) -> FlopWeights:
        """Returns normalized weights for each flop type based on the benchmark results."""
        return FlopWeights(weights=dict())
