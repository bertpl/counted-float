import random

import pytest

from counted_float._core.micro_benchmarking import InterleavedBenchmarkRunner, MicroBenchmark, SliceController
from counted_float._core.micro_benchmarking.output import output_quiet
from counted_float._core.models import MicroBenchmarkResult, SingleRunResult


@pytest.fixture(autouse=True)
def _quiet_console():
    """Silence the shared benchmark console for the runner tests (they assert on results, not output)."""
    with output_quiet(True):
        yield


# =================================================================================================
#  Helpers
# =================================================================================================
class FakeBenchmark(MicroBenchmark):
    """Records every call made to it, both locally and in an optional shared cross-benchmark log."""

    def __init__(self, name: str, shared_log: list[tuple[str, int]] | None = None) -> None:
        super().__init__(name=name)
        self.prepare_suite_calls = 0
        self.slice_log: list[tuple[int, int]] = []  # (n_executions, round_index)
        self.shared_log = shared_log

    def prepare_suite(self, rng: random.Random) -> None:
        self.prepare_suite_calls += 1

    def prepare_slice(self, n_executions: int, round_index: int) -> None:
        self.slice_log.append((n_executions, round_index))
        if self.shared_log is not None:
            self.shared_log.append((self.name, round_index))

    def _prepare_benchmark(self, n_executions: int) -> None:
        pass

    def _run_benchmark(self) -> None:
        pass


class UntimeableBenchmark(FakeBenchmark):
    """A benchmark every one of whose slices measures zero elapsed time.

    What a clock too coarse to resolve a cheap probe produces, made deterministic: the real thing
    depends on machine load, so it surfaces as an occasional crash rather than a reproducible one.
    """

    def run_slice(self, n_executions: int, round_index: int, cpu_freq_mhz: float | None) -> SingleRunResult:
        self.prepare_slice(n_executions, round_index)
        return SingleRunResult(n_executions=n_executions, t_nsecs=0.0, t_cycles=0.0)


# =================================================================================================
#  SliceController
# =================================================================================================
def test_controller_calibration_ramps_aggressively():
    # --- arrange -----------------------------------------
    controller = SliceController(t_slice_target_nsecs=1e6)  # 1 ms target

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs=10.0)  # 1 execution took 10 ns -> way under target

    # --- assert ------------------------------------------
    # rescale factor is clamped to x10 per slice, despite target/actual being 1e5
    assert controller.n_executions == 10
    assert not controller.is_calibrated


def test_controller_calibrates_after_two_on_target_slices():
    # --- arrange -----------------------------------------
    controller = SliceController(t_slice_target_nsecs=1e6)
    controller.n_executions = 1000

    # --- act & assert ------------------------------------
    controller.record_slice(t_nsecs=1.05e6)  # within 20% of target
    assert not controller.is_calibrated
    controller.record_slice(t_nsecs=0.95e6)  # second consecutive on-target slice
    assert controller.is_calibrated


def test_controller_deadband_keeps_n_executions_stable_once_calibrated():
    # --- arrange -----------------------------------------
    controller = SliceController(t_slice_target_nsecs=1e6)
    controller.n_executions = 1000
    controller.record_slice(t_nsecs=1e6)
    controller.record_slice(t_nsecs=1e6)
    assert controller.is_calibrated

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs=1.3e6)  # inside deadband [0.7, 1.4] x target

    # --- assert ------------------------------------------
    assert controller.n_executions == 1000  # no adjustment

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs=5e6)  # far outside deadband

    # --- assert ------------------------------------------
    assert controller.n_executions == 500  # adjustment clamped to /2 (not /5)


def test_controller_execution_count_floor_raises_effective_target():
    # --- arrange -----------------------------------------
    controller = SliceController(t_slice_target_nsecs=1e6)  # 1 ms common target
    controller.n_executions = 1

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs=1e6)  # a single execution already takes the full target

    # --- assert ------------------------------------------
    # effective target floors at N_MIN_EXECUTIONS whole executions
    assert controller.execution_floor_active
    assert controller.t_slice_target_nsecs == SliceController.N_MIN_EXECUTIONS * 1e6


def test_controller_treats_an_unmeasurably_fast_slice_as_far_below_target():
    """A slice measuring zero has no ratio to take, so it must ramp by the full allowed step.

    Reachable whenever a cheap probe at a low execution count finishes below the clock's
    resolution -- the ramp's own starting regime on a coarse-resolution clock, not an exotic case.
    """
    # --- arrange -----------------------------------------
    controller = SliceController(t_slice_target_nsecs=1e6)
    controller.n_executions = 4

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs=0.0)

    # --- assert ------------------------------------------
    assert controller.n_executions == int(4 * SliceController.MAX_ADJUST_FACTOR_CALIBRATION)
    assert not controller.is_calibrated  # a zero slice is not on target


def test_controller_survives_a_zero_slice_once_calibrated():
    """The calibrated deadband path divides by the same measurement, so it needs the same guard."""
    # --- arrange -----------------------------------------
    controller = SliceController(t_slice_target_nsecs=1e6)
    controller.n_executions = 1000  # keeps the per-execution floor below the common target
    controller.record_slice(t_nsecs=1e6)
    controller.record_slice(t_nsecs=1e6)
    assert controller.is_calibrated
    n_before = controller.n_executions

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs=0.0)

    # --- assert ------------------------------------------
    assert controller.n_executions == int(n_before * SliceController.MAX_ADJUST_FACTOR_CALIBRATED)


def test_controller_never_exceeds_absolute_execution_cap():
    # --- arrange -----------------------------------------
    controller = SliceController(t_slice_target_nsecs=1e6)
    controller.n_executions = SliceController.MAX_N_EXECUTIONS

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs=1.0)  # absurdly fast -> wants to scale up

    # --- assert ------------------------------------------
    assert controller.n_executions == SliceController.MAX_N_EXECUTIONS


# =================================================================================================
#  InterleavedBenchmarkRunner
# =================================================================================================
@pytest.fixture
def fake_benchmarks() -> dict[str, FakeBenchmark]:
    return {name: FakeBenchmark(name) for name in ["alpha", "beta", "gamma"]}


def test_runner_returns_requested_number_of_recorded_slices(fake_benchmarks):
    # --- arrange -----------------------------------------
    runner = InterleavedBenchmarkRunner(
        fake_benchmarks, t_slice_target_ms=0.001, n_rounds_measure=7, n_rounds_warmup=2, seed=1
    )

    # --- act ---------------------------------------------
    results = runner.run()

    # --- assert ------------------------------------------
    assert set(results.keys()) == set(fake_benchmarks.keys())
    for result in results.values():
        assert isinstance(result, MicroBenchmarkResult)
        assert len(result.warmup_runs) == 2
        assert len(result.benchmark_runs) == 7


def test_runner_completes_when_every_slice_measures_zero():
    """A full run must survive a probe the clock cannot resolve, rather than dividing by its time."""
    # --- arrange -----------------------------------------
    benchmarks = {name: UntimeableBenchmark(name) for name in ["alpha", "beta"]}
    runner = InterleavedBenchmarkRunner(
        benchmarks, t_slice_target_ms=0.001, n_rounds_measure=3, n_rounds_warmup=1, seed=3
    )

    # --- act ---------------------------------------------
    results = runner.run()

    # --- assert ------------------------------------------
    assert set(results.keys()) == set(benchmarks.keys())
    for result in results.values():
        assert len(result.benchmark_runs) == 3
        # the reported quantiles stay well-defined even though every measurement was zero
        assert result.summary_stats_nsecs_per_exec().q50 == 0.0


def test_runner_prepares_each_suite_exactly_once(fake_benchmarks):
    # --- arrange -----------------------------------------
    runner = InterleavedBenchmarkRunner(
        fake_benchmarks, t_slice_target_ms=0.001, n_rounds_measure=3, n_rounds_warmup=1, seed=1
    )

    # --- act ---------------------------------------------
    runner.run()

    # --- assert ------------------------------------------
    assert all(b.prepare_suite_calls == 1 for b in fake_benchmarks.values())


def test_runner_runs_every_benchmark_exactly_once_per_round(fake_benchmarks):
    # --- arrange -----------------------------------------
    n_rounds_measure, n_rounds_warmup = 5, 2
    runner = InterleavedBenchmarkRunner(
        fake_benchmarks,
        t_slice_target_ms=0.001,
        n_rounds_measure=n_rounds_measure,
        n_rounds_warmup=n_rounds_warmup,
        seed=1,
    )

    # --- act ---------------------------------------------
    runner.run()

    # --- assert ------------------------------------------
    # all benchmarks saw the same number of slices: 1 jit call + shared calibration rounds
    # + warmup rounds + measurement rounds
    slice_counts = {len(b.slice_log) for b in fake_benchmarks.values()}
    assert len(slice_counts) == 1
    # per (recorded) round, every benchmark ran exactly once: the last n_measure+n_warmup
    # round indices per benchmark are 0..n_warmup-1, 0..n_measure-1
    for b in fake_benchmarks.values():
        recorded = [round_index for _, round_index in b.slice_log[-(n_rounds_measure + n_rounds_warmup) :]]
        assert recorded == list(range(n_rounds_warmup)) + list(range(n_rounds_measure))


def test_runner_shuffles_order_between_rounds():
    # --- arrange -----------------------------------------
    # many probes so identical order across all rounds is vanishingly unlikely
    shared_log: list[tuple[str, int]] = []
    names = [f"k{i}" for i in range(10)]
    benchmarks = {name: FakeBenchmark(name, shared_log) for name in names}
    n_rounds_measure = 5
    runner = InterleavedBenchmarkRunner(
        benchmarks,
        t_slice_target_ms=0.001,
        n_rounds_measure=n_rounds_measure,
        n_rounds_warmup=0,
        seed=123,
    )

    # --- act ---------------------------------------------
    runner.run()

    # --- assert ------------------------------------------
    # measurement-phase entries are the last n_rounds_measure * len(names) of the shared log
    measurement_entries = shared_log[-(n_rounds_measure * len(names)) :]
    round_orders = []
    for i in range(n_rounds_measure):
        round_entries = measurement_entries[i * len(names) : (i + 1) * len(names)]
        assert all(round_index == i for _, round_index in round_entries)  # rounds don't interleave
        order = tuple(name for name, _ in round_entries)
        assert sorted(order) == sorted(names)  # every benchmark exactly once per round
        round_orders.append(order)
    assert len(set(round_orders)) > 1  # order is re-shuffled between rounds


def test_runner_schedule_is_reproducible_with_seed():
    # --- arrange -----------------------------------------
    # the seed reproduces the *schedule* (shuffled per-round order) and input pools; the
    # adaptive n_executions still tracks real wall-clock time and is deliberately not pinned
    def run_and_log_schedule(seed: int) -> list[tuple[str, int]]:
        shared_log: list[tuple[str, int]] = []
        benchmarks = {name: FakeBenchmark(name, shared_log) for name in ["alpha", "beta", "gamma"]}
        InterleavedBenchmarkRunner(
            benchmarks, t_slice_target_ms=0.001, n_rounds_measure=4, n_rounds_warmup=1, seed=seed
        ).run()
        return shared_log

    # --- act ---------------------------------------------
    first, second = run_and_log_schedule(seed=7), run_and_log_schedule(seed=7)

    # --- assert ------------------------------------------
    # same warmup + measurement schedule (calibration length may differ: it adapts to timing)
    n_recorded = 5 * 3  # (1 warmup + 4 measure) rounds x 3 benchmarks
    assert first[-n_recorded:] == second[-n_recorded:]


def test_slice_controller_target_is_the_common_target_before_per_exec_timing():
    # before any per-execution timing is recorded, the N_MIN_EXECUTIONS floor cannot apply yet,
    # so the effective target is just the common target
    # --- arrange / act -----------------------------------
    controller = SliceController(t_slice_target_nsecs=1234.0)

    # --- assert ------------------------------------------
    assert controller.t_slice_target_nsecs == 1234.0


# =================================================================================================
#  SliceController - calibration decisions
# =================================================================================================
_TARGET = 1_000.0
_N_EXEC = 1_000


def _fresh_controller() -> SliceController:
    controller = SliceController(_TARGET)
    controller.n_executions = _N_EXEC
    return controller


def _calibrated_controller() -> SliceController:
    """A controller driven to the calibrated state by two consecutive exactly-on-target slices."""
    controller = _fresh_controller()
    controller.record_slice(_TARGET)
    controller.record_slice(_TARGET)
    assert controller.is_calibrated
    assert not controller.execution_floor_active
    return controller


@pytest.mark.parametrize(
    ("t_nsecs", "on_target"),
    [
        (_TARGET * 1.20, True),  # exactly CALIBRATION_TOLERANCE away, inclusive
        (_TARGET * 0.80, True),  # ... and symmetric below
        (_TARGET * 1.21, False),  # just outside
        (_TARGET * 0.79, False),
    ],
)
def test_calibration_tolerance_is_inclusive_at_its_boundary(t_nsecs: float, on_target: bool):
    """Two consecutive slices count as calibrated only while each is within the tolerance."""
    # --- arrange -----------------------------------------
    controller = _fresh_controller()

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs)
    controller.record_slice(t_nsecs)

    # --- assert ------------------------------------------
    assert controller.is_calibrated is on_target


def test_calibration_needs_two_consecutive_on_target_slices():
    """One on-target slice is not enough, and an off-target slice resets the run."""
    # --- arrange -----------------------------------------
    controller = _fresh_controller()

    # --- act & assert ------------------------------------
    controller.record_slice(_TARGET)
    assert not controller.is_calibrated  # one is not enough

    controller.record_slice(_TARGET * 5.0)  # off target: the run restarts from zero
    assert not controller.is_calibrated

    controller.record_slice(_TARGET)
    assert not controller.is_calibrated  # the earlier on-target slice does not still count

    controller.record_slice(_TARGET)
    assert controller.is_calibrated


@pytest.mark.parametrize(
    ("t_nsecs", "expect_adjustment"),
    [
        (_TARGET * 0.70, False),  # exactly DEADBAND_LOW: inside, left alone
        (_TARGET * 1.40, False),  # exactly DEADBAND_HIGH: inside, left alone
        (_TARGET * 0.69, True),  # below the band
        (_TARGET * 1.41, True),  # above the band
    ],
)
def test_calibrated_controller_only_readjusts_outside_the_deadband(t_nsecs: float, expect_adjustment: bool):
    """Noise inside the deadband must not feed back into the next round's workload."""
    # --- arrange -----------------------------------------
    controller = _calibrated_controller()
    n_before = controller.n_executions

    # --- act ---------------------------------------------
    controller.record_slice(t_nsecs)

    # --- assert ------------------------------------------
    assert (controller.n_executions != n_before) is expect_adjustment


def test_a_slice_too_short_to_time_ramps_by_the_maximum_step():
    """A zero-length slice has no ratio to take, so it asks for the largest allowed increase."""
    # --- arrange -----------------------------------------
    controller = SliceController(_TARGET)
    controller.n_executions = 10

    # --- act ---------------------------------------------
    controller.record_slice(0.0)

    # --- assert ------------------------------------------
    assert controller.n_executions == 10 * int(SliceController.MAX_ADJUST_FACTOR_CALIBRATION)
