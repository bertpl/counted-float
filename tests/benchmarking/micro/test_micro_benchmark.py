import time

import pytest

from counted_float._core.benchmarking._output import output_quiet
from counted_float._core.benchmarking.micro import MicroBenchmark
from counted_float._core.models import MicroBenchmarkResult
from counted_float._core.utils import Timer


class DummyMicroBenchmark(MicroBenchmark):
    """Dummy benchmark for testing purposes."""

    def __init__(self, nsecs_per_execution: float):
        super().__init__(name="dummy")
        self.__nsecs_per_execution = nsecs_per_execution
        self.n_calls_prepare_benchmark = 0
        self.n_calls_run_benchmark = 0
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int):
        self.n_calls_prepare_benchmark += 1
        self._n_executions = n_executions

    def _run_benchmark(self):
        self.n_calls_run_benchmark += 1
        self.__sleep(self.__nsecs_per_execution * self._n_executions)  # simulate some work based on n_executions

    @staticmethod
    def __sleep(t_sleep_ns: float):
        # more accurate implementation that time.sleep(...)
        t_start = time.perf_counter_ns()
        while (time.perf_counter_ns() - t_start) < t_sleep_ns:
            pass


@pytest.mark.flaky(reruns=5)  # wall-clock assertions can drift on a loaded CI runner
@pytest.mark.parametrize(
    ("n_runs_total", "n_runs_warmup", "n_seconds_per_run_target"),
    [
        (20, 10, 0.01),
        (20, 5, 0.01),
        (15, 5, 0.02),
        (10, 5, 0.03),
    ],
)
def test_micro_benchmark(n_runs_total: int, n_runs_warmup: int, n_seconds_per_run_target: float):
    # --- arrange -----------------------------------------
    nsec_per_exec = 1_000
    benchmark = DummyMicroBenchmark(nsecs_per_execution=nsec_per_exec)

    expected_run_time_range = [
        0.75 * n_seconds_per_run_target * (n_runs_total - n_runs_warmup),  # minimum expected time
        1.25 * n_seconds_per_run_target * n_runs_total,  # maximum expected time
    ]

    # --- act ---------------------------------------------
    with Timer() as t:
        results = benchmark.run_many(
            n_runs_total=n_runs_total,
            n_runs_warmup=n_runs_warmup,
            n_seconds_per_run_target=n_seconds_per_run_target,
        )

    t_elapsed = t.t_elapsed_sec()

    # --- assert ------------------------------------------
    assert benchmark.n_calls_prepare_benchmark == n_runs_total
    assert benchmark.n_calls_run_benchmark == n_runs_total
    assert expected_run_time_range[0] < t_elapsed < expected_run_time_range[1], "expected run time mismatch"
    assert isinstance(results, MicroBenchmarkResult)
    assert len(results.benchmark_runs) == n_runs_total - n_runs_warmup
    assert len(results.warmup_runs) == n_runs_warmup
    assert results.summary_stats_nsecs_per_exec().q25 < 1.1 * nsec_per_exec, (
        "estimated time range should approx. enclose actual time"
    )
    assert results.summary_stats_nsecs_per_exec().q75 > 0.9 * nsec_per_exec, (
        "estimated time range should approx. enclose actual time"
    )


def test_micro_benchmark_run_many_console_verbosity(capsys):
    """run_many prints per-run progress by default and is fully silent under output_quiet."""
    # --- arrange ----------------------
    benchmark = DummyMicroBenchmark(nsecs_per_execution=1_000)

    # --- act / assert -----------------
    benchmark.run_many(n_runs_total=4, n_runs_warmup=1, n_seconds_per_run_target=0.001)
    assert capsys.readouterr().out != ""  # baseline: progress reaches stdout (confirms capture works)

    with output_quiet(True):
        benchmark.run_many(n_runs_total=4, n_runs_warmup=1, n_seconds_per_run_target=0.001)
    assert capsys.readouterr().out == ""  # silenced: nothing reaches stdout


class FlatRuntimeMicroBenchmark(MicroBenchmark):
    """Benchmark whose runtime does not scale with n_executions, mimicking a dead-code-eliminated kernel."""

    def __init__(self):
        super().__init__(name="flat")
        self.max_n_executions_seen = 0

    def _prepare_benchmark(self, n_executions: int):
        self.max_n_executions_seen = max(self.max_n_executions_seen, n_executions)

    def _run_benchmark(self):
        pass


def test_micro_benchmark_flat_runtime_respects_cap():
    # --- arrange -----------------------------------------
    benchmark = FlatRuntimeMicroBenchmark()

    # --- act ---------------------------------------------
    # default-like parameters; a flat runtime makes the adaptive sizing grow n_executions
    # by MAX_N_EXECUTIONS_FACTOR every run, which must stop at MAX_N_EXECUTIONS
    results = benchmark.run_many(n_runs_total=40, n_runs_warmup=15, n_seconds_per_run_target=0.1)

    # --- assert ------------------------------------------
    assert isinstance(results, MicroBenchmarkResult)
    assert benchmark.max_n_executions_seen == MicroBenchmark.MAX_N_EXECUTIONS
