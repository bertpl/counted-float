"""The flops suite is reached lazily, so an install without its modules gets guidance, not a traceback.

These run in a subprocess with the benchmarking modules made unimportable, which is the only way to
exercise the guard from an environment that does have them installed.
"""

import subprocess
import sys
import textwrap

import pytest

from counted_float._core import benchmarking
from counted_float._core.compatibility import FLOPS_BENCHMARKING

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


# =================================================================================================
#  what stays reachable
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
def test_reaching_the_flops_suite_names_the_extra_that_installs_it():
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        from counted_float._core import benchmarking

        try:
            benchmarking.FlopsBenchmarkSuite
        except ModuleNotFoundError as e:
            print(e)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert "counted-float[" in result.stdout


def test_running_the_flops_benchmark_reports_the_same_guidance():
    # the wrapper resolves the suite itself rather than through the module hook, so it is guarded
    # separately from plain attribute access above
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        from counted_float._core import benchmarking

        try:
            benchmarking.run_flops_benchmark()
        except ModuleNotFoundError as e:
            print(e)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert "counted-float[" in result.stdout


@pytest.mark.skipif(
    not FLOPS_BENCHMARKING.is_importable(),
    reason="the resolving path needs the modules present; the guarded paths are covered above",
)
def test_the_hook_resolves_the_real_suite_when_the_modules_are_there():
    # the happy path of the lazy hook: everything else here exercises it while something is missing
    # --- act ---------------------------------------------
    suite = benchmarking.FlopsBenchmarkSuite

    # --- assert ------------------------------------------
    assert suite is benchmarking.import_flops().FlopsBenchmarkSuite


def test_an_unrelated_import_failure_passes_through_untranslated(monkeypatch):
    # only a missing benchmarking dependency earns the install message; anything else that goes wrong
    # while importing the sub-package must surface as itself, not be relabelled as a packaging problem
    # --- arrange -----------------------------------------
    # a None entry makes the import machinery raise for this module and nothing else, and monkeypatch
    # puts the real entry back afterwards -- no purging of the already-imported package. The parent's
    # attribute goes too: once the sub-package has been imported anywhere, `from . import flops`
    # resolves it straight off the parent and never reaches sys.modules at all.
    monkeypatch.delattr(benchmarking, "flops", raising=False)
    monkeypatch.setitem(sys.modules, "counted_float._core.benchmarking.flops", None)

    # --- act / assert ------------------------------------
    with pytest.raises(ModuleNotFoundError) as excinfo:
        benchmarking.import_flops()

    assert "counted-float[" not in str(excinfo.value)
    assert excinfo.value.name == "counted_float._core.benchmarking.flops"


def test_an_unknown_attribute_still_raises_attribute_error():
    # the hook must not turn every miss into an import attempt
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        from counted_float._core import benchmarking

        try:
            benchmarking.NoSuchThing
        except AttributeError as e:
            print(e)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert "NoSuchThing" in result.stdout
