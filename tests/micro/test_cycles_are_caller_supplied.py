"""Cycles are a view a caller asks for, not something the timing layer reaches out to compute.

The distinction is what keeps the shared micro-benchmark machinery free of psutil: a caller that
reports absolute per-op cost supplies a clock, and one that reports a ratio does not.
"""

import pytest

from counted_float._core.micro import InterleavedBenchmarkRunner, MicroBenchmark
from counted_float._core.models import MicroBenchmarkResult, SingleRunResult

# patched to prove the timing layer never reaches it; it lives behind the benchmarking extra
cpu_freq_module = pytest.importorskip("counted_float._core.benchmarking.flops._cpu_freq")


class _TrivialBenchmark(MicroBenchmark):
    """Minimal concrete benchmark: enough to produce slices, cheap enough to run many of them."""

    def __init__(self) -> None:
        super().__init__(name="trivial", single_execution="x + 1.0")

    def _prepare_benchmark(self, n_executions: int) -> None:
        self._n = n_executions

    def _run_benchmark(self) -> None:
        x = 0.0
        for _ in range(self._n):
            x = x + 1.0


def _result_without_cycles() -> MicroBenchmarkResult:
    runs = [SingleRunResult(n_executions=10, t_nsecs=100.0, t_cycles=None) for _ in range(4)]
    return MicroBenchmarkResult(warmup_runs=[], benchmark_runs=runs)


# =================================================================================================
#  the timing layer without a clock
# =================================================================================================
def test_a_slice_carries_no_cycles_when_no_clock_was_supplied():
    # --- arrange -----------------------------------------
    benchmark = _TrivialBenchmark()

    # --- act ---------------------------------------------
    result = benchmark.run_slice(n_executions=10, round_index=0, cpu_freq_mhz=None)

    # --- assert ------------------------------------------
    assert result.t_nsecs > 0
    assert result.t_cycles is None
    assert result.cycles_per_exec() is None


def test_a_slice_carries_cycles_when_a_clock_was_supplied():
    # --- arrange -----------------------------------------
    benchmark = _TrivialBenchmark()

    # --- act ---------------------------------------------
    result = benchmark.run_slice(n_executions=10, round_index=0, cpu_freq_mhz=1000.0)

    # --- assert ------------------------------------------
    assert result.t_cycles is not None
    assert result.cycles_per_exec() == result.t_cycles / 10


def test_the_runner_reads_no_clock_unless_given_a_source():
    # the property that keeps psutil out of the shared layer -- asserted by making the read fail
    # rather than by inspecting imports, since a reachable-but-unused import is not the problem
    # --- arrange -----------------------------------------
    def explode(*args: object, **kwargs: object) -> float:
        raise AssertionError("the timing layer read a CPU frequency without being asked to")

    original = cpu_freq_module._get_psutil_cpu_freq_attribute_mhz
    cpu_freq_module._get_psutil_cpu_freq_attribute_mhz = explode
    try:
        runner = InterleavedBenchmarkRunner(
            benchmarks={"a": _TrivialBenchmark()},
            t_slice_target_ms=0.1,
            n_rounds_measure=2,
            n_rounds_warmup=1,
            seed=1,
        )

        # --- act -----------------------------------------
        results = runner.run()
    finally:
        cpu_freq_module._get_psutil_cpu_freq_attribute_mhz = original

    # --- assert ------------------------------------------
    assert results["a"].has_cycle_counts() is False


def test_the_runner_stamps_the_clock_its_source_returns():
    # --- arrange -----------------------------------------
    runner = InterleavedBenchmarkRunner(
        benchmarks={"a": _TrivialBenchmark()},
        t_slice_target_ms=0.1,
        n_rounds_measure=2,
        n_rounds_warmup=1,
        seed=1,
        cpu_freq_source=lambda: 2500.0,
    )

    # --- act ---------------------------------------------
    results = runner.run()

    # --- assert ------------------------------------------
    assert results["a"].has_cycle_counts() is True


# =================================================================================================
#  asking for cycles that were never measured
# =================================================================================================
def test_cycle_quantiles_refuse_rather_than_invent_a_clock():
    # the old behavior silently substituted a nominal 1 GHz, so the reported "cycles" were
    # nanoseconds under another name -- a caller that never supplied a clock should hear about it
    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="no cycle counts"):
        _result_without_cycles().get_cycles_per_exec_quantile(q=0.5)


def test_has_cycle_counts_reports_what_was_measured():
    # --- act / assert ------------------------------------
    assert _result_without_cycles().has_cycle_counts() is False
