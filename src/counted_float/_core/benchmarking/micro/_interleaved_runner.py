"""Round-robin interleaved execution of a set of micro-benchmarks.

Instead of running each benchmark as one contiguous block (where a transient
contention burst or thermal drift hits one benchmark and not its subtraction
partner), all benchmarks advance together in short time slices: any
machine-wide disturbance hits every benchmark approximately equally and
cancels in downstream pairwise differences.  Residual per-benchmark noise is
handled by a low-quantile estimator over the recorded slices.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Generic, TypeVar

from counted_float._core.models import MicroBenchmarkResult
from counted_float._core.utils import get_cpu_frequency_mhz_current

if TYPE_CHECKING:
    from collections.abc import Mapping

    from counted_float._core.models import SingleRunResult

    from ._micro_benchmark import MicroBenchmark

K = TypeVar("K")


# =================================================================================================
#  Per-benchmark slice controller
# =================================================================================================
class SliceController:
    """Adapts one benchmark's ``n_executions`` so each slice hits its wall-time target.

    Two regimes:
      - calibration: aggressive rescaling (factor clamped to x/÷10 per slice) until the
        slice time lands within CALIBRATION_TOLERANCE of target on two consecutive slices
      - calibrated: a deadband controller — only re-adjust when the slice fell outside
        [DEADBAND_LOW, DEADBAND_HIGH] x target, clamped to x/÷2 per adjustment — so noise
        excursions don't feed back into the workload of subsequent rounds

    The effective target is floored at N_MIN_EXECUTIONS whole executions per slice, so an
    expensive benchmark on slow hardware overshoots the common wall-time target instead of
    starving on integer-``n_executions`` granularity.
    """

    MAX_ADJUST_FACTOR_CALIBRATION = 10.0
    MAX_ADJUST_FACTOR_CALIBRATED = 2.0
    MAX_N_EXECUTIONS = 10**12  # same overflow backstop as MicroBenchmark.run_many
    CALIBRATION_TOLERANCE = 0.2
    DEADBAND_LOW = 0.7
    DEADBAND_HIGH = 1.4
    N_MIN_EXECUTIONS = 32

    def __init__(self, t_slice_target_nsecs: float) -> None:
        self.t_slice_common_target_nsecs = t_slice_target_nsecs
        self.n_executions = 1
        self.is_calibrated = False
        self._n_consecutive_on_target = 0
        self._t_per_exec_nsecs: float | None = None

    # --- properties --------------------------------------
    @property
    def t_slice_target_nsecs(self) -> float:
        """Effective slice target: the common target, floored at N_MIN_EXECUTIONS executions."""
        if self._t_per_exec_nsecs is None:
            return self.t_slice_common_target_nsecs
        return max(self.t_slice_common_target_nsecs, self.N_MIN_EXECUTIONS * self._t_per_exec_nsecs)

    @property
    def execution_floor_active(self) -> bool:
        """True if the N_MIN_EXECUTIONS floor pushed this benchmark's target above the common one."""
        return self.t_slice_target_nsecs > self.t_slice_common_target_nsecs

    # --- main API -----------------------------------------
    def record_slice(self, t_nsecs: float) -> None:
        """Update controller state after a slice that took t_nsecs in total."""
        self._t_per_exec_nsecs = t_nsecs / self.n_executions
        target = self.t_slice_target_nsecs
        if not self.is_calibrated:
            if abs(t_nsecs - target) <= self.CALIBRATION_TOLERANCE * target:
                self._n_consecutive_on_target += 1
                if self._n_consecutive_on_target >= 2:
                    self.is_calibrated = True
            else:
                self._n_consecutive_on_target = 0
            self._rescale(target / t_nsecs, max_factor=self.MAX_ADJUST_FACTOR_CALIBRATION)
        elif not (self.DEADBAND_LOW * target <= t_nsecs <= self.DEADBAND_HIGH * target):
            self._rescale(target / t_nsecs, max_factor=self.MAX_ADJUST_FACTOR_CALIBRATED)

    # --- internals ----------------------------------------
    def _rescale(self, factor: float, max_factor: float) -> None:
        factor = max(1 / max_factor, min(max_factor, factor))
        self.n_executions = max(1, min(self.MAX_N_EXECUTIONS, int(self.n_executions * factor)))


# =================================================================================================
#  Interleaved runner
# =================================================================================================
class InterleavedBenchmarkRunner(Generic[K]):
    """Runs a set of MicroBenchmarks in round-robin interleaved fashion.

    Phases:
      1. setup     — each benchmark's one-time ``prepare_suite`` (buffer allocation, input pools)
      2. JIT pass  — one 1-execution call per benchmark, forcing jit compilation outside timing
      3. calibration rounds (discarded) — adaptive ramp of each benchmark's ``n_executions``
      4. warmup rounds (recorded as warmup) — full-length rounds at stable ``n_executions``,
         bringing the CPU to the thermal/frequency steady state measurement will run in
      5. measurement rounds (recorded) — benchmark order re-shuffled every round so periodic
         system activity decorrelates from benchmark identity

    The CPU frequency is sampled once per round and stamped onto all of that round's slices.
    """

    N_ROUNDS_CALIBRATION_MAX = 10

    def __init__(
        self,
        benchmarks: Mapping[K, MicroBenchmark],
        t_slice_target_ms: float = 20.0,
        n_rounds_measure: int = 200,
        n_rounds_warmup: int = 3,
        seed: int | None = None,
        show_progress: bool = True,
    ) -> None:
        self.benchmarks = benchmarks
        self.t_slice_target_ms = t_slice_target_ms
        self.n_rounds_measure = n_rounds_measure
        self.n_rounds_warmup = n_rounds_warmup
        self.seed = seed
        self.show_progress = show_progress

    def run(self) -> dict[K, MicroBenchmarkResult]:
        """Run all phases and return one MicroBenchmarkResult per benchmark."""
        # independent per-phase rngs: the calibration phase consumes a timing-dependent
        # number of shuffles, so isolating it keeps the warmup/measurement schedule and the
        # input pools reproducible for a given seed
        master_rng = random.Random(self.seed)  # noqa: S311 -- reproducible benchmark scheduling, not crypto
        rng_pool, rng_calibration, rng_schedule = (
            random.Random(master_rng.random())  # noqa: S311 -- reproducible benchmark scheduling, not crypto
            for _ in range(3)
        )
        controllers = {key: SliceController(self.t_slice_target_ms * 1e6) for key in self.benchmarks}
        warmup_runs: dict[K, list[SingleRunResult]] = {key: [] for key in self.benchmarks}
        benchmark_runs: dict[K, list[SingleRunResult]] = {key: [] for key in self.benchmarks}

        # --- phase 1+2: setup & JIT pass -----------------
        self._print("setup ")
        for benchmark in self.benchmarks.values():
            benchmark.prepare_suite(rng_pool)
        cpu_freq_mhz = get_cpu_frequency_mhz_current()
        for key, benchmark in self.benchmarks.items():
            result = benchmark.run_slice(n_executions=1, round_index=0, cpu_freq_mhz=cpu_freq_mhz)
            controllers[key].record_slice(result.t_nsecs)

        # --- phase 3: calibration rounds -----------------
        self._print("calibrate ")
        for round_index in range(self.N_ROUNDS_CALIBRATION_MAX):
            if all(c.is_calibrated for c in controllers.values()):
                break
            self._run_round(rng_calibration, controllers, round_index, record_into=None)

        # --- phase 4+5: warmup & measurement rounds ------
        self._print("warmup ")
        for round_index in range(self.n_rounds_warmup):
            self._run_round(rng_schedule, controllers, round_index, record_into=warmup_runs)
        self._print("measure ")
        for round_index in range(self.n_rounds_measure):
            self._run_round(rng_schedule, controllers, round_index, record_into=benchmark_runs)
            if (round_index + 1) % 10 == 0:
                self._print(".")
        self._print(" done\n")

        # --- report + return -----------------------------
        floored = [str(key) for key, c in controllers.items() if c.execution_floor_active]
        if floored:
            self._print(f"note: minimum-executions floor was active for: {', '.join(floored)}\n")
        return {
            key: MicroBenchmarkResult(warmup_runs=warmup_runs[key], benchmark_runs=benchmark_runs[key])
            for key in self.benchmarks
        }

    # --- internals ----------------------------------------
    def _run_round(
        self,
        rng: random.Random,
        controllers: dict[K, SliceController],
        round_index: int,
        record_into: dict[K, list[SingleRunResult]] | None,
    ) -> None:
        """Run one round: every benchmark exactly once, in a freshly shuffled order."""
        keys = list(self.benchmarks.keys())
        rng.shuffle(keys)
        cpu_freq_mhz = get_cpu_frequency_mhz_current()  # once per round, stamped onto all its slices
        for key in keys:
            controller = controllers[key]
            result = self.benchmarks[key].run_slice(
                n_executions=controller.n_executions,
                round_index=round_index,
                cpu_freq_mhz=cpu_freq_mhz,
            )
            controller.record_slice(result.t_nsecs)
            if record_into is not None:
                record_into[key].append(result)

    def _print(self, text: str) -> None:
        if self.show_progress:
            print(text, end="", flush=True)
