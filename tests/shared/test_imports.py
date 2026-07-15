import importlib
import subprocess
import sys
import textwrap


def test_import_all_counted_float():
    """Check if importing all elements of __all__ from counted_float always works."""
    from counted_float import __all__ as public_names

    for item in public_names:
        _ = getattr(importlib.import_module("counted_float"), item)


def test_import_all_counted_float_config():
    """Check if importing all elements of __all__ from counted_float.config always works."""
    from counted_float.config import __all__ as public_names

    for item in public_names:
        _ = getattr(importlib.import_module("counted_float.config"), item)


def test_import_all_counted_float_benchmarking():
    """Check if importing all elements of __all__ from counted_float.benchmarking always works."""
    from counted_float.benchmarking import __all__ as public_names

    for item in public_names:
        _ = getattr(importlib.import_module("counted_float.benchmarking"), item)


def test_bare_import_does_not_load_numba():
    # benchmarking pulls in numba/llvmlite, the bulk of this package's import cost; importers
    # that only count flops must not pay for it, so the subpackage resolves on first access
    code = textwrap.dedent(
        """
        import sys
        import counted_float
        eager = [m for m in ("numba", "llvmlite") if m in sys.modules]
        sys.exit(1 if eager else 0)
        """
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)  # noqa: S603 -- fixed args, no user input
    assert result.returncode == 0, "importing counted_float eagerly loaded numba"


def test_benchmarking_still_resolves_after_bare_import():
    code = textwrap.dedent(
        """
        import counted_float
        assert counted_float.benchmarking.__name__ == "counted_float.benchmarking"
        """
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)  # noqa: S603 -- fixed args, no user input
    assert result.returncode == 0, "counted_float.benchmarking did not resolve on attribute access"
