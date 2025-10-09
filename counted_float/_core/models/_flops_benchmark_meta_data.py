from __future__ import annotations

import platform
from importlib.metadata import PackageNotFoundError, version

import cpuinfo
import psutil

from counted_float._core.utils import get_cpu_frequency_mhz_max, get_cpu_frequency_mhz_min

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
    processor: ProcessorInfo
    os: OSInfo
    python: PythonInfo
    packages: PackagesInfo

    @classmethod
    def from_system(cls) -> SystemInfo:
        return SystemInfo(
            processor=ProcessorInfo.from_system(),
            os=OSInfo.from_system(),
            python=PythonInfo.from_system(),
            packages=PackagesInfo.from_system(),
        )


# =================================================================================================
#  Sub-models
# =================================================================================================
class ProcessorInfo(MyBaseModel):
    description: str
    architecture: str
    n_logical_core_count: int
    n_physical_core_count: int
    min_freq_mhz: int | None
    max_freq_mhz: int | None

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
            min_freq_mhz=int(get_cpu_frequency_mhz_min() or 0.0) or None,
            max_freq_mhz=int(get_cpu_frequency_mhz_max() or 0.0) or None,
        )


class OSInfo(MyBaseModel):
    platform: str
    system: str
    release: str
    version: str

    @classmethod
    def from_system(cls) -> OSInfo:
        return OSInfo(
            platform=platform.platform(),
            system=platform.system(),
            release=platform.release(),
            version=platform.version(),
        )


class PythonInfo(MyBaseModel):
    version: str
    implementation: str
    compiler: str

    @classmethod
    def from_system(cls) -> PythonInfo:
        return PythonInfo(
            version=platform.python_version(),
            implementation=platform.python_implementation(),
            compiler=platform.python_compiler(),
        )


class PackagesInfo(MyBaseModel):
    counted_float: str
    llvmlite: str
    numba: str
    numpy: str
    psutil: str
    py_cpuinfo: str

    @classmethod
    def from_system(cls) -> PackagesInfo:
        def get_package_version(_package: str) -> str:
            try:
                return version(_package)
            except PackageNotFoundError:
                return "<not_installed>"

        return PackagesInfo(
            counted_float=get_package_version("counted-float"),
            llvmlite=get_package_version("llvmlite"),
            numba=get_package_version("numba"),
            numpy=get_package_version("numpy"),
            psutil=get_package_version("psutil"),
            py_cpuinfo=get_package_version("py-cpuinfo"),
        )
