from __future__ import annotations

import platform
from importlib.metadata import PackageNotFoundError, version

from .base import JsonReprModel


# =================================================================================================
#  Benchmark Settings
# =================================================================================================
class BenchmarkSettings(JsonReprModel):
    """Settings the round-robin interleaved benchmark run was collected with.

    The fields describing the run shape are optional so a partial or future-scheme
    settings block still parses. Data collected under the earlier contiguous-block
    scheme carried `n_runs_total` / `n_runs_warmup` / `n_seconds_per_run_target`
    instead; those fields have been retired, and since the model ignores unknown keys,
    such older or externally-saved results still parse (the retired keys are dropped).
    """

    array_size: int
    t_slice_target_ms: float | None = None
    n_rounds_measure: int | None = None
    n_rounds_warmup: int | None = None
    input_pool_size: int | None = None
    order_shuffled: bool | None = None


# =================================================================================================
#  System Info
# =================================================================================================
class SystemInfo(JsonReprModel):
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
class ProcessorInfo(JsonReprModel):
    description: str
    architecture: str
    n_logical_core_count: int | None
    n_physical_core_count: int | None
    min_freq_mhz: int | None
    max_freq_mhz: int | None

    @classmethod
    def from_system(cls) -> ProcessorInfo:
        """Describe the running machine's processor, as stamped onto a benchmark result."""
        # psutil, cpuinfo and the cpu_freq helpers sit behind the `benchmarking` extra, which only
        # ProcessorInfo.from_system needs. The required() guard gives a base install -- which ships
        # SystemInfo as public API but not the extra -- an actionable message rather than a bare
        # ModuleNotFoundError; the imports stay deferred so that loading the model to parse shipped
        # data never pulls the extra in. The resulting upward models -> benchmarking dependency is
        # accepted, since from_system runs only while benchmarking.
        from counted_float._core.compatibility import Capability

        with Capability.FLOPS_BENCHMARKING.required():
            import cpuinfo
            import psutil

            from counted_float._core.benchmarking.flops.cpu_freq import (
                get_cpu_frequency_mhz_max,
                get_cpu_frequency_mhz_min,
            )

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


class OSInfo(JsonReprModel):
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


class PythonInfo(JsonReprModel):
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


class PackagesInfo(JsonReprModel):
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
