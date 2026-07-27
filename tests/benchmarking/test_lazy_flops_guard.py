"""The flops suite is reached lazily, so an install without the extra gets guidance, not a traceback.

Two techniques, because two different things are being claimed:

- **Subprocess with the modules blocked** — proves what stays *reachable* on an install that does
  not carry them. Import-time reachability is the claim, so it has to be a fresh interpreter.
- **Patched availability** — proves the guard fires. A capability is absent when its distribution is
  not installed, which cannot be faked by blocking an import, so the availability lookup is what
  gets replaced. CI exercises the real thing on the legs installed without the extra.
"""

import subprocess
import sys
import textwrap

import pytest

import counted_float._core.compatibility._optional_dependencies as optional_dependencies
from counted_float._core import benchmarking
from counted_float._core.compatibility import CAP_FLOPS_BENCHMARKING, MissingCapabilityError
from tests._capabilities import needs

_BLOCK_BENCHMARKING_MODULES = """
    import sys

    BLOCKED = {"numba", "numpy", "psutil", "cpuinfo"}

    class Blocker:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in BLOCKED:
                raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
            return None

    for name in [n for n in sys.modules if n.split(".")[0] in BLOCKED]:
        del sys.modules[name]
    sys.meta_path.insert(0, Blocker())
"""


def _run_without_benchmarking_modules(body: str) -> subprocess.CompletedProcess[str]:
    """Run a snippet in a fresh interpreter where the benchmarking modules cannot be imported."""
    script = textwrap.dedent(_BLOCK_BENCHMARKING_MODULES) + textwrap.dedent(body)
    # the interpreter is this one and the script is the literal above, so there is no untrusted input
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )


@pytest.fixture
def extra_not_installed(monkeypatch):
    """Make every capability read as absent, as it would be on an install without the extra."""
    monkeypatch.setattr(optional_dependencies, "is_available", lambda _: False)


# =================================================================================================
#  what stays reachable without the extra
# =================================================================================================
def test_counting_works_without_the_benchmarking_modules():
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        from counted_float import CountedFloat, FlopCountingContext

        with FlopCountingContext() as ctx:
            _ = CountedFloat(2.0) * CountedFloat(3.0) + CountedFloat(1.0)
        print(ctx.flop_counts().ADD, ctx.flop_counts().MUL)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1 1"


def test_the_benchmarking_package_still_imports_without_them():
    # the overhead benchmark and the result model must survive the flops suite becoming unreachable
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        from counted_float.benchmarking import FlopsBenchmarkResults, run_counted_float_benchmark

        print(FlopsBenchmarkResults.__name__, run_counted_float_benchmark.__name__)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "FlopsBenchmarkResults run_counted_float_benchmark"


def test_the_shipped_benchmark_data_still_parses_without_them():
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        from counted_float import BuiltInData

        print(len(BuiltInData.benchmarks()) > 0)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


# =================================================================================================
#  what is guarded
# =================================================================================================
def test_reaching_the_flops_suite_names_the_extra_that_installs_it(extra_not_installed):
    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError, match=r"counted-float\[numba\]"):
        _ = benchmarking.FlopsBenchmarkSuite


def test_running_the_flops_benchmark_reports_the_same_guidance(extra_not_installed):
    # the wrapper resolves the suite itself rather than through the module hook, so it is guarded
    # separately from plain attribute access above
    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError, match=r"counted-float\[numba\]"):
        benchmarking.run_flops_benchmark()


def test_the_guard_refuses_before_importing_anything(extra_not_installed, monkeypatch):
    # a precondition, not a rescued failure: with the extra absent the import is never attempted, so
    # a heavy sub-package is not half-loaded on the way to an error
    # --- arrange -----------------------------------------
    monkeypatch.delattr(benchmarking, "flops", raising=False)
    monkeypatch.delitem(sys.modules, "counted_float._core.benchmarking.flops", raising=False)

    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError):
        benchmarking.import_flops()

    assert "counted_float._core.benchmarking.flops" not in sys.modules


# =================================================================================================
#  with the extra present
# =================================================================================================
@needs(CAP_FLOPS_BENCHMARKING)
def test_the_hook_resolves_the_real_suite():
    # --- act ---------------------------------------------
    suite = benchmarking.FlopsBenchmarkSuite

    # --- assert ------------------------------------------
    assert suite is benchmarking.import_flops().FlopsBenchmarkSuite


def test_an_unknown_attribute_still_raises_attribute_error():
    # the hook must not turn every miss into an import attempt
    # --- act / assert ------------------------------------
    with pytest.raises(AttributeError, match="NoSuchThing"):
        _ = benchmarking.NoSuchThing
