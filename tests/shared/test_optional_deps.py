import importlib

import pytest

from counted_float._core._optional_deps import FLAG_BENCHMARK_DEPS, requires_benchmark_deps


# =================================================================================================
#  Flag
# =================================================================================================
@pytest.mark.requires_benchmarking_deps
def test_flag_benchmark_deps_true():
    """Check if this flag is set to True if [benchmark] dependencies are available."""
    assert FLAG_BENCHMARK_DEPS


@pytest.mark.requires_no_benchmarking_deps
def test_flag_benchmark_deps_false():
    """Check if this flag is set to False if [benchmark] dependencies are NOT available."""
    assert not FLAG_BENCHMARK_DEPS


# =================================================================================================
#  Decorator
# =================================================================================================
@requires_benchmark_deps
def decorated_function(a: int):
    return a + 1


@pytest.mark.requires_benchmarking_deps
def test_benchmark_decorator_with_deps():
    """Check if decorator works correctly if [benchmark] dependencies are available."""
    assert decorated_function(1) == 2


@pytest.mark.requires_no_benchmarking_deps
def test_benchmark_decorator_without_deps():
    """Check if decorator works correctly if [benchmark] dependencies are NOT available."""
    with pytest.raises(ImportError):
        decorated_function(1)  # error only raised when called, not when defined


# =================================================================================================
#  Misc
# =================================================================================================
def test_import_all_counted_float():
    """Check if importing all elements of __all__ from counted_float always works."""
    from counted_float import __all__ as ALL

    for item in ALL:
        _ = getattr(importlib.import_module("counted_float"), item)


def test_import_all_counted_float_benchmarking():
    """Check if importing all elements of __all__ from counted_float.benchmarking always works."""
    from counted_float.benchmarking import __all__ as ALL

    for item in ALL:
        _ = getattr(importlib.import_module("counted_float.benchmarking"), item)
