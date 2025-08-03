from abc import ABC, abstractmethod

from counted_float._core._optional_deps import requires_benchmark_deps

from ._models import MicroBenchmarkResult, SingleRunResult
from ._time_utils import Timer, format_time_durations


# =================================================================================================
#  Base class for micro-benchmarks
# =================================================================================================
class MicroBenchmark(ABC):
    """
    Base class for micro-benchmarks, where a child class needs to implement the following methods:
      _prepare_benchmark --> prepares the benchmark_runs (e.g. sets up data); is called once before each _run_benchmark
                                and time spent here is not counted.
      _run_benchmark     --> runs the benchmark_runs; is called multiple times and time spent here is counted.

    NOTE: this essentially offers similar functionality as the python-builtin timeit module, but with some benefits:
            - automatic resizing of the benchmark_runs to achieve a target time per run
            - automatic warmup_runs runs
            - robust computation of median run time and ± range based on quantiles, rather than mean & std.
                  (=more robust to outliers)
    """

    MAX_N_OPERATIONS_FACTOR = 10  # never adjust n_operations by more than this factor (up or down)

    @requires_benchmark_deps
    def __init__(self, name: str):
        self.name = name

    def run_many(
        self, n_runs_total: int = 20, n_runs_warmup: int = 5, n_seconds_per_run_target: float = 0.5
    ) -> MicroBenchmarkResult:
        """
        Runs the MicroBenchmark multiple times (warmup_runs & actual test runs), with provided parameters and returns
        (q25, q50, q75) quantiles of run times in nanoseconds.
        :param n_runs_total: (int, default=20) total number of benchmark_runs runs
        :param n_runs_warmup: (int, default=5) number of warmup_runs runs
                                             - the first n_runs_warmup of n_runs_total are not included in timing stats
                                             - warmup_runs runs serve to initialize n_operations & get processor, cache, ...
                                                 in a stable, representative state
        :param n_seconds_per_run_target: (float, default=0.5) target time (sec) per benchmark_runs run (prepare + run).
                                             n_operations will be iteratively adjusted to achieve this target time.
        """

        print(f"{self.name.ljust(30)}: ", end="")

        # repeat benchmark_runs n_runs_total times
        n_operations = 1  # start with a benchmark_runs of 1 operation and scale up as needed
        warmup_runs: list[SingleRunResult] = []
        benchmark_runs: list[SingleRunResult] = []
        for i in range(n_runs_total):
            # --- run benchmark_runs ---
            with Timer() as t:
                single_run_result = self.run_once(n_operations)
            t_tot_seconds = t.t_elapsed_sec()  # total time (sec) of prepare + run

            # --- capture result ---
            if i < n_runs_warmup:
                # warmup run that doesn't count
                print("w", end="", flush=True)
                warmup_runs.append(single_run_result)
            else:
                # benchmark run that does count
                print(".", end="", flush=True)
                benchmark_runs.append(single_run_result)

            # --- adjust n_ops ---
            n_ops_min = max(1, int(n_operations / self.MAX_N_OPERATIONS_FACTOR))
            n_ops_max = int(n_operations * self.MAX_N_OPERATIONS_FACTOR)
            n_operations = max(n_ops_min, min(n_ops_max, int(n_operations * n_seconds_per_run_target / t_tot_seconds)))

        # final results
        benchmark_result = MicroBenchmarkResult(
            warmup_runs=warmup_runs,
            benchmark_runs=benchmark_runs,
        )
        stats = benchmark_result.summary_stats()
        print(f"   {format_time_durations(nsec_q25=stats.q25, nsec_q50=stats.q50, nsec_q75=stats.q75)}")

        # return quantiles
        return benchmark_result

    def run_once(self, n_operations: int) -> SingleRunResult:
        """Runs benchmark_runs once for a given # of operations and returns time in nanoseconds per operation"""

        # prepare
        self._prepare_benchmark(n_operations)

        # run
        with Timer() as t:
            self._run_benchmark()

        # report
        return SingleRunResult(
            n_operations=n_operations,
            t_nsecs=t.t_elapsed_nsec(),
        )

    @abstractmethod
    def _prepare_benchmark(self, n_operations: int):
        """
        Prepare benchmark_runs (e.g. set up data) based on requested number of operations.  This argument is adjusted each
          run by the MicroBenchmarkRunner class to ensure that the benchmark_runs runs for a reasonable amount of time
            (e.g. 1 second per run).
        """
        raise NotImplementedError()

    @abstractmethod
    def _run_benchmark(self):
        """Run benchmark_runs.  This method is called multiple times and the time spent here is measured."""
        raise NotImplementedError()
