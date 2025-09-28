from __future__ import annotations

import platform
from importlib.metadata import PackageNotFoundError, version

import cpuinfo
import psutil

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
    package_info: PackageInfo
    platform_processor: str
    platform_machine: str
    platform_system: str
    platform_release: str
    platform_python_version: str
    platform_python_implementation: str
    platform_python_compiler: str
    psutil_cpu_count_logical: int
    psutil_cpu_count_physical: int
    psutil_cpu_freq_mhz: int = 1_000  # default value for backwards compatibility with older benchmark results

    @classmethod
    def from_system(cls) -> SystemInfo:
        return SystemInfo(
            package_info=PackageInfo.from_system(),
            platform_processor=platform.processor(),
            platform_machine=platform.machine(),
            platform_system=platform.system(),
            platform_release=platform.release(),
            platform_python_version=platform.python_version(),
            platform_python_implementation=platform.python_implementation(),
            platform_python_compiler=platform.python_compiler(),
            psutil_cpu_count_logical=psutil.cpu_count(logical=True),
            psutil_cpu_count_physical=psutil.cpu_count(logical=False),
            psutil_cpu_freq_mhz=int(psutil.cpu_freq().current),
        )


class PackageInfo(MyBaseModel):
    counted_float: str
    llvmlite: str
    numba: str
    numpy: str
    psutil: str
    py_cpuinfo: str

    @classmethod
    def from_system(cls) -> PackageInfo:
        def get_package_version(_package: str) -> str:
            try:
                return version(_package)
            except PackageNotFoundError:
                return "<not_installed>"

        return PackageInfo(
            counted_float=get_package_version("counted-float"),
            llvmlite=get_package_version("llvmlite"),
            numba=get_package_version("numba"),
            numpy=get_package_version("numpy"),
            psutil=get_package_version("psutil"),
            py_cpuinfo=get_package_version("py-cpuinfo"),
        )


class ProcessorInfo(MyBaseModel):
    description: str
    architecture: str
    n_logical_core_count: int
    n_physical_core_count: int
    min_freq_mhz: int
    max_freq_mhz: int

    @classmethod
    def from_system(cls) -> ProcessorInfo:
        cpu_info_dict = cpuinfo.get_cpu_info()
        return ProcessorInfo(
            description=cpu_info_dict.get("brand_raw", ""),
            architecture=" - ".join(
                [
                    s
                    for s in [
                        cpu_info_dict.get("arch_string_raw"),
                        cpu_info_dict.get("arch"),
                        f"{cpu_info_dict.get('bits')}-bits" if cpu_info_dict.get("bits") else None,
                    ]
                    if s
                ]
            ),
            n_logical_core_count=psutil.cpu_count(logical=True),
            n_physical_core_count=psutil.cpu_count(logical=False),
            min_freq_mhz=int(psutil.cpu_freq().min),
            max_freq_mhz=int(psutil.cpu_freq().max),
        )
