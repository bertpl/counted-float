from counted_float._core.models._flops_benchmark_meta_data import PackageInfo


def test_package_info():
    # --- act ---------------------------------------------
    package_info = PackageInfo.from_system()

    # --- assert ------------------------------------------
    assert isinstance(package_info, PackageInfo)
    assert "." in package_info.counted_float
    assert ("." in package_info.numba) or (package_info.numba == "<not_installed>")  # optional
    assert "." in package_info.numpy  # not optional
    assert "." in package_info.psutil  # not optional
