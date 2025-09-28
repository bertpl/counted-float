from counted_float._core.models._flops_benchmark_meta_data import PackageInfo, SystemInfo


def test_system_info():
    # --- act ---------------------------------------------
    system_info = SystemInfo.from_system()

    # --- assert ------------------------------------------
    assert isinstance(system_info, SystemInfo)


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

