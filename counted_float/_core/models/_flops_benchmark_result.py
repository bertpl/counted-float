from __future__ import annotations

from ._base import MyBaseModel
from ._flop_type import FlopType
from ._flop_weights import FlopWeights
from ._micro_benchmark_result import Quantiles


# =================================================================================================
#  Flops Benchmark Metadata
# =================================================================================================
class SystemInfo(MyBaseModel):
    platform_processor: str
    platform_machine: str
    platform_system: str
    platform_release: str
    platform_python_version: str
    platform_python_implementation: str
    platform_python_compiler: str
    psutil_cpu_count_logical: int
    psutil_cpu_count_physical: int
    psutil_cpu_freq_mhz: int = 1_000  # for backwards compatibility with older benchmark results


class BenchmarkSettings(MyBaseModel):
    array_size: int
    n_runs_total: int
    n_runs_warmup: int
    n_seconds_per_run_target: float


# =================================================================================================
#  Main Flops Benchmark Information
# =================================================================================================
class FlopsBenchmarkDurations(MyBaseModel):
    # baseline + flops benchmarking results in nanoseconds per <array_size> flops
    baseline: Quantiles
    flops: dict[FlopType, Quantiles]


class FlopsBenchmarkResults(MyBaseModel):
    system_info: SystemInfo
    benchmark_settings: BenchmarkSettings
    results_ns: FlopsBenchmarkDurations

    @property
    def flop_weights(self) -> FlopWeights:
        """
        Returns normalized weights for each flop type based on the benchmark results.
           1) first of all, we only consider median values of the benchmark results
           2) compute duration for each flop type _minus_ baseline duration per <array_size> flops
           3) convert to flop weights by taking a few simple flop types as reference (see FlopWeights implementation)
        """

        # step 1) collect median values for all results
        median_baseline_ns = self.results_ns.baseline.q50
        median_flops_ns = {k: v.q50 for k, v in self.results_ns.flops.items()}

        # step 2) surplus durations for each flop type, on top of baseline duration
        flop_durations_ns = {flop_type: median_flops_ns[flop_type] - median_baseline_ns for flop_type in FlopType}

        # step 3) convert to FlopWeights
        return FlopWeights.from_abs_flop_costs(flop_costs=flop_durations_ns)
