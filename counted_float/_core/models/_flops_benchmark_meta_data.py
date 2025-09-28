from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

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


class PackageInfo(MyBaseModel):
    counted_float: str
    numba: str
    numpy: str
    psutil: str

    @classmethod
    def from_system(cls):
        def get_package_version(_package: str) -> str:
            try:
                return version(_package)
            except PackageNotFoundError:
                return "<not_installed>"

        return PackageInfo(
            counted_float=get_package_version("counted_float"),
            numba=get_package_version("numba"),
            numpy=get_package_version("numpy"),
            psutil=get_package_version("psutil"),
        )
