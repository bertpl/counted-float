import random
from abc import ABC, abstractmethod

from counted_float._core.benchmarking._output import console
from counted_float._core.models import MicroBenchmarkResult, SingleRunResult
from counted_float._core.utils import (
    Timer,
    convert_nsecs_to_cycles,
    format_latency,
    format_time_duration,
    get_cpu_frequency_mhz_current,
)


# =================================================================================================
#  Base class for micro-benchmarks
# =================================================================================================
class MicroBenchmark(ABC):
    """Base class for micro-benchmarks, where a child class needs to implement the abstract methods below.

      _prepare_benchmark --> prepares the benchmark_runs (e.g. sets up data); is called once before each _run_benchmark
                                and time spent here is not counted.
      _run_benchmark     --> runs the benchmark_runs; is called multiple times and time spent here is counted.

    NOTE: this essentially offers similar functionality as the python-builtin timeit module, but with some benefits:
            - automatic resizing of the benchmark_runs to achieve a target time per run
            - automatic warmup_runs runs
            - robust computation of median run time and ± range based on quantiles, rather than mean & std.
                  (=more robust to outliers)
    """

    MAX_N_EXECUTIONS_FACTOR = 10  # never adjust n_executions by more than this factor (up or down)
    MAX_N_EXECUTIONS = 10**12  # absolute cap; unbounded growth (e.g. when a jit-compiled probe is
    #                            dead-code-eliminated and runtime stays flat) would overflow int64

    def __init__(self, name: str, single_execution: str = "execution") -> None:
        self.name = name
        self.single_execution = single_execution

    def run_many(
        self, n_runs_total: int = 20, n_runs_warmup: int = 5, n_seconds_per_run_target: float = 0.5
    ) -> MicroBenchmarkResult:
        """Run the MicroBenchmark multiple times and return (q25, q50, q75) quantiles of run times in nanoseconds.

        Per-run progress goes to the shared benchmark console (silenced via output_quiet).

        Runs consist of warmup_runs & actual test runs, with the provided parameters.

        Args:
            n_runs_total: Total number of runs.
            n_runs_warmup: How many leading runs are warmup rather than measurement. They are
                excluded from the timing stats, and serve to settle n_executions and to bring the
                processor, caches and so on into a stable, representative state.
            n_seconds_per_run_target: Target wall time per run (prepare + run), in seconds.
                n_executions is iteratively adjusted to hit it.
        """
        console.print(f"{self.name.ljust(35)}: ", end="")

        # repeat benchmark_runs n_runs_total times
        n_executions = 1  # start with a benchmark_runs of 1 operation and scale up as needed
        warmup_runs: list[SingleRunResult] = []
        benchmark_runs: list[SingleRunResult] = []
        for i in range(n_runs_total):
            # --- run benchmark_runs ---
            with Timer() as t:
                single_run_result = self.run_once(n_executions)
            # floored: an immeasurably fast run must not divide the rescale below by zero
            t_tot_seconds = max(t.t_elapsed_sec(), 1e-9)  # total time (sec) of prepare + run

            # --- capture result ---
            if i < n_runs_warmup:
                # warmup run that doesn't count
                console.print("w", end="")
                warmup_runs.append(single_run_result)
            else:
                # benchmark run that does count
                console.print(".", end="")
                benchmark_runs.append(single_run_result)

            # --- adjust n_ops ---
            n_ops_min = max(1, int(n_executions / self.MAX_N_EXECUTIONS_FACTOR))
            n_ops_max = min(int(n_executions * self.MAX_N_EXECUTIONS_FACTOR), self.MAX_N_EXECUTIONS)
            n_executions = max(n_ops_min, min(n_ops_max, int(n_executions * n_seconds_per_run_target / t_tot_seconds)))

        # final results
        benchmark_result = MicroBenchmarkResult(
            warmup_runs=warmup_runs,
            benchmark_runs=benchmark_runs,
        )

        # display duration estimates
        stats_nsecs = benchmark_result.summary_stats_nsecs_per_exec()
        stats_cycles = benchmark_result.summary_stats_cycles_per_exec()
        s_time_duration = f"{format_time_duration(stats_nsecs.q50)}{stats_nsecs.format_uncertainty_suffix()}"
        s_latency = f"{format_latency(stats_cycles.q50)}{stats_cycles.format_uncertainty_suffix()}"
        console.print(f"   [{s_time_duration} | {s_latency} ]  /  {self.single_execution}")

        # return final result
        return benchmark_result

    def prepare_suite(self, rng: random.Random) -> None:  # noqa: B027 -- optional hook, deliberately non-abstract
        """One-time setup before interleaved execution (buffer allocation, input pools).

        Default: no-op — subclasses that pre-generate data override this; ``rng`` makes
        that generation reproducible when the caller passes a seeded instance.
        """

    def prepare_slice(self, n_executions: int, round_index: int) -> None:
        """Cheap per-slice preparation for interleaved execution.

        Default: falls back to the full per-run preparation.  Subclasses that allocate
        persistently in ``prepare_suite`` override this with a cheap variant (e.g. input
        pool slot selection) so the gap between timed regions stays negligible.
        """
        self._prepare_benchmark(n_executions)

    def run_slice(self, n_executions: int, round_index: int, cpu_freq_mhz: float | None) -> SingleRunResult:
        """Run one interleaved slice: cheap preparation + one timed call.

        Unlike ``run_once``, the CPU frequency is passed in by the caller (sampled once
        per round) instead of being read per call.
        """
        self.prepare_slice(n_executions, round_index)
        with Timer() as t:
            self._run_benchmark()
        return SingleRunResult(
            n_executions=n_executions,
            t_nsecs=t.t_elapsed_nsec(),
            t_cycles=convert_nsecs_to_cycles(nsec=t.t_elapsed_nsec(), cpu_freq_mhz=cpu_freq_mhz),
        )

    def run_once(self, n_executions: int) -> SingleRunResult:
        """Run benchmark_runs once for a given # of executions and return time per execution.

        Time is returned in nanoseconds & cpu cycles.
        """
        # prepare
        self._prepare_benchmark(n_executions)

        # run
        with Timer() as t:
            self._run_benchmark()

        # report
        return SingleRunResult(
            n_executions=n_executions,
            t_nsecs=t.t_elapsed_nsec(),
            t_cycles=convert_nsecs_to_cycles(nsec=t.t_elapsed_nsec(), cpu_freq_mhz=get_cpu_frequency_mhz_current()),
        )

    @abstractmethod
    def _prepare_benchmark(self, n_executions: int) -> None:
        """Prepare benchmark_runs (e.g. set up data) based on requested number of executions.

        This argument is adjusted each run by the MicroBenchmarkRunner class to ensure that the benchmark_runs
        runs for a reasonable amount of time (e.g. 1 second per run).
        """
        ...

    @abstractmethod
    def _run_benchmark(self) -> None:
        """Run benchmark_runs.  This method is called multiple times and the time spent here is measured."""
        ...
