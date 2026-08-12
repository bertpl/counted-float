"""Running the flops suite without its extra reports what to install, rather than failing obscurely.

Two techniques, because two different things are being claimed:

- **Subprocess with the modules blocked** — proves what stays *importable* on an install that does
  not carry them. Import-time reachability is the claim, so it needs a fresh interpreter.
- **Patched availability** — proves the guard fires. A capability is absent when its distribution is
  not installed, which cannot be faked by blocking an import, so the availability lookup is what
  gets replaced. CI exercises the real thing on the legs installed without the extra.
"""

import re
import subprocess
import sys
import textwrap

import pytest

from counted_float._core import benchmarking
from counted_float._core.compatibility import Capability, MissingCapabilityError
from counted_float._core.models.flops_benchmark_meta_data import ProcessorInfo
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
    monkeypatch.setattr(Capability, "is_available", lambda _: False)


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
    # the result model and the deprecated alias must survive the flops suite becoming unreachable --
    # the package has to stay importable for its own guard to be able to report anything
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        import warnings

        from counted_float.benchmarking import FlopsBenchmarkResults

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from counted_float.benchmarking import run_counted_float_benchmark

        print(FlopsBenchmarkResults.__name__, run_counted_float_benchmark.__name__)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "FlopsBenchmarkResults evaluate_counting_overhead"


def test_the_shipped_benchmark_data_still_parses_without_them():
    # --- act ---------------------------------------------
    result = _run_without_benchmarking_modules("""
        from counted_float import BuiltInData

        print(len(BuiltInData.benchmarks()) > 0)
    """)

    # --- assert ------------------------------------------
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


def test_holding_the_entry_point_costs_nothing_without_the_extra(extra_not_installed):
    # the guard sits inside the call rather than at module level, so having the function in hand is
    # free: nothing raises until someone actually asks for a benchmark
    # --- act / assert ------------------------------------
    assert callable(benchmarking.run_flops_benchmark)


# =================================================================================================
#  what is guarded
# =================================================================================================
def test_running_the_flops_benchmark_names_the_extra_that_installs_it(extra_not_installed):
    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError, match=re.escape(f"counted-float[{Capability.FLOPS_BENCHMARKING}]")):
        benchmarking.run_flops_benchmark()


def test_the_guard_refuses_before_importing_anything(extra_not_installed, monkeypatch):
    # a precondition, not a rescued failure: with the extra absent the import is never attempted, so
    # a heavy sub-package is not half-loaded on the way to an error
    # --- arrange -----------------------------------------
    monkeypatch.delattr(benchmarking, "flops", raising=False)
    monkeypatch.delitem(sys.modules, "counted_float._core.benchmarking.flops", raising=False)

    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError):
        benchmarking.run_flops_benchmark()

    assert "counted_float._core.benchmarking.flops" not in sys.modules


def test_stamping_the_running_machine_names_the_extra_that_installs_it(extra_not_installed):
    # ProcessorInfo.from_system reaches the benchmarking-only cpu probes; without the extra the call
    # must name what to install rather than surface a bare ModuleNotFoundError
    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError, match=re.escape(f"counted-float[{Capability.FLOPS_BENCHMARKING}]")):
        ProcessorInfo.from_system()


# =================================================================================================
#  with the extra present
# =================================================================================================
@needs(Capability.FLOPS_BENCHMARKING)
def test_the_suite_runs_when_the_extra_is_there():
    # --- act ---------------------------------------------
    result = benchmarking.run_flops_benchmark(
        t_slice_target_ms=0.1, n_rounds_measure=5, n_rounds_warmup=1, seed=42, verbose=False
    )

    # --- assert ------------------------------------------
    assert result is not None
