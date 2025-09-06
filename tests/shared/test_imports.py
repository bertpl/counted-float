import importlib


def test_import_all_counted_float():
    """Check if importing all elements of __all__ from counted_float always works."""
    from counted_float import __all__ as ALL

    for item in ALL:
        _ = getattr(importlib.import_module("counted_float"), item)


def test_import_all_counted_float_config():
    """Check if importing all elements of __all__ from counted_float.config always works."""
    from counted_float.config import __all__ as ALL

    for item in ALL:
        _ = getattr(importlib.import_module("counted_float.config"), item)


def test_import_all_counted_float_benchmarking():
    """Check if importing all elements of __all__ from counted_float.benchmarking always works."""
    from counted_float.benchmarking import __all__ as ALL

    for item in ALL:
        _ = getattr(importlib.import_module("counted_float.benchmarking"), item)
