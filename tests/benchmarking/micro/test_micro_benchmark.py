"""MicroBenchmark.run_many's control logic: adaptive sizing, the warmup split, and quantile stats.

The subject is a feedback controller -- each run rescales n_executions from the previous run's
Timer reading toward the per-run time target. Timing enters only through time.perf_counter_ns(),
so most of these tests drive a fake clock that only the benchmark's simulated work advances:
every assertion is exact and immune to a loaded runner. One test at the bottom does exercise the
real clock, asserting only a floor, so faking cannot hide a benchmark loop that never times
anything.
"""

import time

import pytest

from counted_float._core.benchmarking._output import output_quiet
from counted_float._core.benchmarking.micro import MicroBenchmark
from counted_float._core.models import MicroBenchmarkResult


# =================================================================================================
#  Fake clock & simulated benchmarks
# =================================================================================================
class FakeClock:
    """perf_counter_ns() stand-in that only moves when simulated work advances it."""

    def __init__(self) -> None:
        self.now_ns = 1_000_000

    def advance(self, nsecs: float) -> None:
        self.now_ns += int(nsecs)

    def read(self) -> int:
        return self.now_ns


@pytest.fixture
def fake_clock(monkeypatch) -> FakeClock:
    """Route every Timer reading to a FakeClock and return it."""
    clock = FakeClock()
    monkeypatch.setattr(time, "perf_counter_ns", clock.read)
    return clock


class ClockAdvancingBenchmark(MicroBenchmark):
    """Simulates nsecs_per_execution of work per execution by advancing the fake clock."""

    def __init__(self, clock: FakeClock, nsecs_per_execution: float):
        super().__init__(name="fake")
        self.nsecs_per_execution = nsecs_per_execution
        self.n_executions_per_run: list[int] = []  # doubles as the _prepare_benchmark call log
        self._clock = clock
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int):
        self._n_executions = n_executions
        self.n_executions_per_run.append(n_executions)

    def _run_benchmark(self):
        self._clock.advance(self.nsecs_per_execution * self._n_executions)


class BusyWaitBenchmark(MicroBenchmark):
    """Performs real work: busy-waits nsecs_per_execution of real wall-clock time per execution."""

    def __init__(self, nsecs_per_execution: float):
        super().__init__(name="busy-wait")
        self.nsecs_per_execution = nsecs_per_execution
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int):
        self._n_executions = n_executions

    def _run_benchmark(self):
        t_start = time.perf_counter_ns()
        while (time.perf_counter_ns() - t_start) < self.nsecs_per_execution * self._n_executions:
            pass


# =================================================================================================
#  Adaptive sizing of n_executions
# =================================================================================================
def test_run_many_ramps_n_executions_to_the_target(fake_clock):
    """Growth is clamped to MAX_N_EXECUTIONS_FACTOR per step, then holds at the converged size."""
    # --- arrange -----------------------------------------
    benchmark = ClockAdvancingBenchmark(fake_clock, nsecs_per_execution=1_000)

    # --- act ---------------------------------------------
    benchmark.run_many(n_runs_total=20, n_runs_warmup=5, n_seconds_per_run_target=0.01)

    # --- assert ------------------------------------------
    # 0.01 s target / 1 us per execution converges at 10_000; the ramp toward it is bounded
    # by the 10x per-step growth clamp
    assert benchmark.n_executions_per_run == [1, 10, 100, 1_000] + [10_000] * 16


def test_run_many_shrinks_n_executions_when_the_cost_jumps(fake_clock):
    """A run overshooting the target shrinks the next run, clamped to the same factor."""

    # --- arrange -----------------------------------------
    class CostJumpBenchmark(ClockAdvancingBenchmark):
        """Cost per execution jumps 1000x from the seventh run onward."""

        def _prepare_benchmark(self, n_executions: int):
            if len(self.n_executions_per_run) == 6:
                self.nsecs_per_execution = 1_000_000
            super()._prepare_benchmark(n_executions)

    benchmark = CostJumpBenchmark(fake_clock, nsecs_per_execution=1_000)

    # --- act ---------------------------------------------
    benchmark.run_many(n_runs_total=12, n_runs_warmup=5, n_seconds_per_run_target=0.01)

    # --- assert ------------------------------------------
    # up-ramp as before; the 1000x cost jump at run 6 overshoots the target 1000x, and the
    # controller walks back down 10x per step until it re-converges at 10
    assert benchmark.n_executions_per_run == [1, 10, 100, 1_000, 10_000, 10_000, 10_000, 1_000, 100, 10, 10, 10]


def test_run_many_flat_runtime_respects_the_cap(fake_clock):
    """A runtime that stays flat as n_executions grows (dead-code-eliminated kernel) drives
    unbounded growth, which must stop at MAX_N_EXECUTIONS."""

    # --- arrange -----------------------------------------
    class FlatRuntimeBenchmark(ClockAdvancingBenchmark):
        """Takes 1 ns per run regardless of n_executions."""

        def _run_benchmark(self):
            self._clock.advance(1)

    benchmark = FlatRuntimeBenchmark(fake_clock, nsecs_per_execution=0)

    # --- act ---------------------------------------------
    benchmark.run_many(n_runs_total=15, n_runs_warmup=5, n_seconds_per_run_target=0.1)

    # --- assert ------------------------------------------
    assert benchmark.n_executions_per_run == [10 ** min(i, 12) for i in range(15)]
    assert max(benchmark.n_executions_per_run) == MicroBenchmark.MAX_N_EXECUTIONS


def test_run_many_survives_runs_measuring_zero_elapsed_time(fake_clock):
    """Every run measuring exactly 0 ns (dead-code-eliminated kernel on a coarse-resolution clock)
    must still produce a result and a report, not a ZeroDivisionError."""
    # --- arrange -----------------------------------------
    benchmark = ClockAdvancingBenchmark(fake_clock, nsecs_per_execution=0)

    # --- act ---------------------------------------------
    results = benchmark.run_many(n_runs_total=15, n_runs_warmup=5, n_seconds_per_run_target=0.1)

    # --- assert ------------------------------------------
    assert isinstance(results, MicroBenchmarkResult)
    assert results.summary_stats_nsecs_per_exec().q50 == 0.0
    assert max(benchmark.n_executions_per_run) == MicroBenchmark.MAX_N_EXECUTIONS  # 1e-9 floor, then capped


# =================================================================================================
#  Warmup split & quantile stats
# =================================================================================================
@pytest.mark.parametrize(
    ("n_runs_total", "n_runs_warmup"),
    [
        (20, 10),
        (20, 5),
        (10, 3),
    ],
)
def test_run_many_splits_warmup_from_benchmark_runs(fake_clock, n_runs_total: int, n_runs_warmup: int):
    # --- arrange -----------------------------------------
    benchmark = ClockAdvancingBenchmark(fake_clock, nsecs_per_execution=1_000)

    # --- act ---------------------------------------------
    results = benchmark.run_many(
        n_runs_total=n_runs_total,
        n_runs_warmup=n_runs_warmup,
        n_seconds_per_run_target=0.01,
    )

    # --- assert ------------------------------------------
    assert isinstance(results, MicroBenchmarkResult)
    assert len(benchmark.n_executions_per_run) == n_runs_total
    assert len(results.warmup_runs) == n_runs_warmup
    assert len(results.benchmark_runs) == n_runs_total - n_runs_warmup
    # the warmup runs are the *first* runs, in order
    assert [r.n_executions for r in results.warmup_runs] == benchmark.n_executions_per_run[:n_runs_warmup]
    assert [r.n_executions for r in results.benchmark_runs] == benchmark.n_executions_per_run[n_runs_warmup:]


def test_run_many_stats_recover_the_cost_per_execution(fake_clock):
    # --- arrange -----------------------------------------
    nsecs_per_execution = 1_000
    benchmark = ClockAdvancingBenchmark(fake_clock, nsecs_per_execution=nsecs_per_execution)

    # --- act ---------------------------------------------
    results = benchmark.run_many(n_runs_total=20, n_runs_warmup=5, n_seconds_per_run_target=0.01)

    # --- assert ------------------------------------------
    # every run measures exactly nsecs_per_execution per execution, so all quantiles equal it
    stats = results.summary_stats_nsecs_per_exec()
    assert stats.q25 == stats.q50 == stats.q75 == nsecs_per_execution


# =================================================================================================
#  Console output
# =================================================================================================
def test_run_many_console_verbosity(capsys):
    """run_many prints per-run progress by default and is fully silent under output_quiet."""
    # --- arrange ----------------------
    benchmark = BusyWaitBenchmark(nsecs_per_execution=1_000)

    # --- act / assert -----------------
    benchmark.run_many(n_runs_total=4, n_runs_warmup=1, n_seconds_per_run_target=0.001)
    assert capsys.readouterr().out != ""  # baseline: progress reaches stdout (confirms capture works)

    with output_quiet(True):
        benchmark.run_many(n_runs_total=4, n_runs_warmup=1, n_seconds_per_run_target=0.001)
    assert capsys.readouterr().out == ""  # silenced: nothing reaches stdout


# =================================================================================================
#  Against the real clock
# =================================================================================================
def test_run_many_measures_the_real_clock():
    """Insurance against the fake clock hiding a benchmark loop that never times anything.

    Asserts only a floor: the busy-wait guarantees a minimum of real elapsed time per execution,
    never a maximum, and how far a loaded runner overshoots is not something run_many promises
    anything about.
    """
    # --- arrange -----------------------------------------
    nsecs_per_execution = 1_000
    benchmark = BusyWaitBenchmark(nsecs_per_execution=nsecs_per_execution)

    # --- act ---------------------------------------------
    results = benchmark.run_many(n_runs_total=5, n_runs_warmup=2, n_seconds_per_run_target=0.001)

    # --- assert ------------------------------------------
    assert results.summary_stats_nsecs_per_exec().q25 >= nsecs_per_execution
