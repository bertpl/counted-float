import time

import pytest

from counted_float._core.benchmarking._micro_benchmark import MicroBenchmark
from counted_float._core.benchmarking._models import MicroBenchmarkResult
from counted_float._core.benchmarking._time_utils import Timer


class DummyMicroBenchmark(MicroBenchmark):
    """Dummy benchmark for testing purposes."""

    def __init__(self, nsecs_per_operation: float):
        super().__init__(name="dummy")
        self.__nsecs_per_operation = nsecs_per_operation
        self.n_calls_prepare_benchmark = 0
        self.n_calls_run_benchmark = 0
        self._n_operations = 1

    def _prepare_benchmark(self, n_operations: int):
        self.n_calls_prepare_benchmark += 1
        self._n_operations = n_operations

    def _run_benchmark(self):
        self.n_calls_run_benchmark += 1
        self.__sleep(self.__nsecs_per_operation * self._n_operations)  # simulate some work based on n_operations

    @staticmethod
    def __sleep(t_sleep_ns: float):
        # more accurate implementation that time.sleep(...)
        t_start = time.perf_counter_ns()
        while (time.perf_counter_ns() - t_start) < t_sleep_ns:
            pass


@pytest.mark.parametrize(
    "n_runs_total, n_runs_warmup, n_seconds_per_run_target",
    [
        (20, 10, 0.01),
        (20, 5, 0.01),
        (15, 5, 0.02),
        (10, 5, 0.03),
    ],
)
def test_micro_benchmark(n_runs_total: int, n_runs_warmup: int, n_seconds_per_run_target: float):
    # --- arrange -----------------------------------------
    nsec_per_op = 1_000
    benchmark = DummyMicroBenchmark(nsecs_per_operation=nsec_per_op)

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
    assert results.summary_stats().q25 < 1.1 * nsec_per_op, "estimated time range should approx. enclose actual time"
    assert results.summary_stats().q75 > 0.9 * nsec_per_op, "estimated time range should approx. enclose actual time"
