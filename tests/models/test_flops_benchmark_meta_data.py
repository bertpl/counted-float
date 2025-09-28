from counted_float._core.models._flops_benchmark_meta_data import (
    OSInfo,
    PackageInfo,
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
    package_info = PackageInfo.from_system()

    # --- assert ------------------------------------------
    assert isinstance(package_info, PackageInfo)
    assert "." in package_info.counted_float
    assert ("." in package_info.llvmlite) or (package_info.llvmlite == "<not_installed>")  # optional
    assert ("." in package_info.numba) or (package_info.numba == "<not_installed>")  # optional
    assert "." in package_info.numpy  # not optional
    assert "." in package_info.psutil  # not optional
    assert "." in package_info.py_cpuinfo  # not optional
