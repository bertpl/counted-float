import platform
from importlib.metadata import PackageNotFoundError

import pytest

import counted_float._core.models._flops_benchmark_meta_data as meta
from counted_float._core.models._flops_benchmark_meta_data import (
    BenchmarkSettings,
    OSInfo,
    PackagesInfo,
    ProcessorInfo,
    PythonInfo,
    SystemInfo,
)

# the models themselves parse the shipped data without either module; only stamping the *running*
# machine onto a fresh benchmark reads them, which is what this module exercises
cpuinfo = pytest.importorskip("cpuinfo", reason="describing the running machine reads py-cpuinfo")
psutil = pytest.importorskip("psutil", reason="describing the running machine reads psutil")


# =================================================================================================
#  SystemInfo
# =================================================================================================
def test_system_info():
    # --- act ---------------------------------------------
    system_info = SystemInfo.from_system()

    # --- assert ------------------------------------------
    assert isinstance(system_info, SystemInfo)


# =================================================================================================
#  Sub-models
# =================================================================================================
def test_processor_info():
    # --- act ---------------------------------------------
    processor_info = ProcessorInfo.from_system()

    # --- assert ------------------------------------------
    assert isinstance(processor_info, ProcessorInfo)


def test_processor_info_records_undetectable_core_count_as_none(monkeypatch):
    # psutil.cpu_count() returns None when the count can't be determined; from_system must
    # record that as None instead of raising a validation error
    # --- arrange -----------------------------------------
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: None)

    # --- act ---------------------------------------------
    processor_info = ProcessorInfo.from_system()

    # --- assert ------------------------------------------
    assert processor_info.n_logical_core_count is None
    assert processor_info.n_physical_core_count is None


def test_os_info():
    # --- act ---------------------------------------------
    os_info = OSInfo.from_system()
    os_info.show()

    # --- assert ------------------------------------------
    assert isinstance(os_info, OSInfo)


def test_python_info():
    # --- act ---------------------------------------------
    python_info = PythonInfo.from_system()

    # --- assert ------------------------------------------
    assert isinstance(python_info, PythonInfo)


def test_package_info():
    # --- act ---------------------------------------------
    package_info = PackagesInfo.from_system()

    # --- assert ------------------------------------------
    assert isinstance(package_info, PackagesInfo)
    assert "." in package_info.counted_float
    assert ("." in package_info.llvmlite) or (package_info.llvmlite == "<not_installed>")  # optional
    assert ("." in package_info.numba) or (package_info.numba == "<not_installed>")  # optional
    assert "." in package_info.numpy  # not optional
    assert "." in package_info.psutil  # not optional
    assert "." in package_info.py_cpuinfo  # not optional


# =================================================================================================
#  from_system() field mapping (host calls mocked, so each field's source is pinned)
# =================================================================================================
def test_processor_info_maps_each_host_fact_to_its_field(monkeypatch):
    # distinct mocked values so a swapped field or flag is caught
    # --- arrange -----------------------------------------
    monkeypatch.setattr(
        cpuinfo,
        "get_cpu_info",
        lambda: {"brand_raw": "Test CPU", "arch_string_raw": "x86_64", "arch": "X86_64", "bits": 64},
    )
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: 8 if logical else 4)
    monkeypatch.setattr(meta, "get_cpu_frequency_mhz_min", lambda: 1000.0)
    monkeypatch.setattr(meta, "get_cpu_frequency_mhz_max", lambda: 3000.0)

    # --- act ---------------------------------------------
    info = ProcessorInfo.from_system()

    # --- assert ------------------------------------------
    assert info.description == "Test CPU"
    assert info.architecture == "x86_64 - X86_64 - 64-bits"
    assert info.n_logical_core_count == 8  # logical=True
    assert info.n_physical_core_count == 4  # logical=False
    assert info.min_freq_mhz == 1000
    assert info.max_freq_mhz == 3000


def test_processor_info_architecture_drops_absent_parts_and_freq_none_stays_none(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(
        cpuinfo,
        "get_cpu_info",
        lambda: {"brand_raw": "CPU", "arch_string_raw": "arm64", "arch": None, "bits": None},
    )
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: 1)
    monkeypatch.setattr(meta, "get_cpu_frequency_mhz_min", lambda: None)
    monkeypatch.setattr(meta, "get_cpu_frequency_mhz_max", lambda: None)

    # --- act ---------------------------------------------
    info = ProcessorInfo.from_system()

    # --- assert ------------------------------------------
    assert info.architecture == "arm64"  # arch and bits absent -> only arch_string_raw, no blank joins
    assert info.min_freq_mhz is None  # a None reading maps to None, not 0
    assert info.max_freq_mhz is None


def test_processor_info_defaults_description_and_architecture_to_empty(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(cpuinfo, "get_cpu_info", dict)  # nothing detected
    monkeypatch.setattr(psutil, "cpu_count", lambda logical=True: None)
    monkeypatch.setattr(meta, "get_cpu_frequency_mhz_min", lambda: 500.0)
    monkeypatch.setattr(meta, "get_cpu_frequency_mhz_max", lambda: 500.0)

    # --- act ---------------------------------------------
    info = ProcessorInfo.from_system()

    # --- assert ------------------------------------------
    assert info.description == ""  # brand_raw absent -> "" default
    assert info.architecture == ""  # no parts present


def test_os_info_maps_platform_calls_to_fields(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(platform, "platform", lambda: "PLATFORM")
    monkeypatch.setattr(platform, "system", lambda: "SYSTEM")
    monkeypatch.setattr(platform, "release", lambda: "RELEASE")
    monkeypatch.setattr(platform, "version", lambda: "VERSION")

    # --- act ---------------------------------------------
    info = OSInfo.from_system()

    # --- assert ------------------------------------------
    assert (info.platform, info.system, info.release, info.version) == ("PLATFORM", "SYSTEM", "RELEASE", "VERSION")


def test_python_info_maps_platform_calls_to_fields(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(platform, "python_version", lambda: "3.13.0")
    monkeypatch.setattr(platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(platform, "python_compiler", lambda: "Clang 1")

    # --- act ---------------------------------------------
    info = PythonInfo.from_system()

    # --- assert ------------------------------------------
    assert (info.version, info.implementation, info.compiler) == ("3.13.0", "CPython", "Clang 1")


def test_packages_info_queries_each_fields_own_package(monkeypatch):
    # version() echoes the package name, so each field must query its own package literal
    # --- arrange -----------------------------------------
    monkeypatch.setattr(meta, "version", lambda pkg: f"v-{pkg}")

    # --- act ---------------------------------------------
    info = PackagesInfo.from_system()

    # --- assert ------------------------------------------
    assert info.counted_float == "v-counted-float"
    assert info.llvmlite == "v-llvmlite"
    assert info.numba == "v-numba"
    assert info.numpy == "v-numpy"
    assert info.psutil == "v-psutil"
    assert info.py_cpuinfo == "v-py-cpuinfo"


def test_packages_info_reports_not_installed_for_missing_package(monkeypatch):
    # --- arrange -----------------------------------------
    def _raise_not_found(pkg):
        raise PackageNotFoundError(pkg)

    monkeypatch.setattr(meta, "version", _raise_not_found)

    # --- act ---------------------------------------------
    info = PackagesInfo.from_system()

    # --- assert ------------------------------------------
    assert info.numba == "<not_installed>"


# =================================================================================================
#  BenchmarkSettings
# =================================================================================================
def test_benchmark_settings_still_parses_retired_legacy_fields():
    # a settings block from the retired contiguous scheme must still parse: the retired
    # keys are unknown now and silently ignored (model default extra="ignore")
    # --- arrange -----------------------------------------
    legacy = {"array_size": 1000, "n_runs_total": 40, "n_runs_warmup": 15, "n_seconds_per_run_target": 0.1}

    # --- act ---------------------------------------------
    settings = BenchmarkSettings(**legacy)

    # --- assert ------------------------------------------
    assert settings.array_size == 1000
    assert not hasattr(settings, "n_runs_total")  # retired field is dropped, not stored
    assert settings.t_slice_target_ms is None


def test_benchmark_settings_round_trips_interleaved_scheme():
    # --- arrange -----------------------------------------
    settings = BenchmarkSettings(
        array_size=1000,
        t_slice_target_ms=20.0,
        n_rounds_measure=200,
        n_rounds_warmup=3,
        input_pool_size=4,
        order_shuffled=True,
    )

    # --- act ---------------------------------------------
    parsed = BenchmarkSettings.model_validate_json(settings.model_dump_json())

    # --- assert ------------------------------------------
    assert parsed == settings
    # the serialized form no longer carries the retired legacy keys
    assert "n_runs_total" not in settings.model_dump_json()
