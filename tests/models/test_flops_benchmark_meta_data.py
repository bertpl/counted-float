from counted_float._core.models._flops_benchmark_meta_data import (
    BenchmarkSettings,
    OSInfo,
    PackagesInfo,
    ProcessorInfo,
    PythonInfo,
    SystemInfo,
)


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
#  BenchmarkSettings
# =================================================================================================
def test_benchmark_settings_parses_legacy_contiguous_scheme():
    # --- arrange -----------------------------------------
    # settings block as embedded in data files collected with the contiguous scheme
    legacy = {"array_size": 1000, "n_runs_total": 40, "n_runs_warmup": 15, "n_seconds_per_run_target": 0.1}

    # --- act ---------------------------------------------
    settings = BenchmarkSettings(**legacy)

    # --- assert ------------------------------------------
    assert settings.array_size == 1000
    assert settings.n_runs_total == 40
    assert settings.t_slice_target_ms is None
    assert settings.order_shuffled is None


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
    assert parsed.n_runs_total is None
