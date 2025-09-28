from __future__ import annotations

from importlib.metadata import version

from ._base import MyBaseModel


# =================================================================================================
#  Benchmark Settings
# =================================================================================================
class BenchmarkSettings(MyBaseModel):
    array_size: int
    n_runs_total: int
    n_runs_warmup: int
    n_seconds_per_run_target: float


# =================================================================================================
#  System Info
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

