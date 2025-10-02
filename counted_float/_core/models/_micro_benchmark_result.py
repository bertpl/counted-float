from __future__ import annotations

import numpy as np

from ._base import MyBaseModel


class SingleRunResult(MyBaseModel):
    """Result of a single run of our micro-benchmark_runs for a give # of executions."""

    n_executions: int
    t_nsecs: float  # total elapsed time in nanoseconds
    t_cycles: float  # total elapsed time in cpu cycles (using psutil.cpu_freq().current)

    def nsecs_per_exec(self) -> float:
        return self.t_nsecs / self.n_executions

    def cycles_per_exec(self) -> float:
        return self.t_cycles / self.n_executions


class Quantiles(MyBaseModel):
    """Class to represent a fixed set of quantiles of an (empirical) distribution."""

    q25: float
    q50: float
    q75: float

    def format_uncertainty(self) -> str:
        # return uncertainty as a % in string format
        return f"{50 * (self.q75 - self.q25) / self.q50:4.1f}%"


class MicroBenchmarkResult(MyBaseModel):
    """Results of all runs in the micro-benchmark_runs (warmup_runs + actual benchmark_runs runs)."""

    warmup_runs: list[SingleRunResult]
    benchmark_runs: list[SingleRunResult]

    def get_nsecs_per_exec_quantile(self, q: float) -> float:
        """Returns a specific quantile of all results in the 'benchmark_runs' category expressed as nsecs/execution."""
        return float(np.quantile([el.nsecs_per_exec() for el in self.benchmark_runs], q))

    def get_cycles_per_exec_quantile(self, q: float) -> float:
        """Returns a specific quantile of all results in the 'benchmark_runs' category expressed as cycles/execution."""
        return float(np.quantile([el.cycles_per_exec() for el in self.benchmark_runs], q))

    def summary_stats_nsecs_per_exec(self) -> Quantiles:
        # summary statistics of nsecs_per_exec
        return Quantiles(
            q25=self.get_nsecs_per_exec_quantile(q=0.25),
            q50=self.get_nsecs_per_exec_quantile(q=0.50),
            q75=self.get_nsecs_per_exec_quantile(q=0.75),
        )

    def summary_stats_cycles_per_exec(self) -> Quantiles:
        # summary statistics of cycles_per_exec
        return Quantiles(
            q25=self.get_cycles_per_exec_quantile(q=0.25),
            q50=self.get_cycles_per_exec_quantile(q=0.50),
            q75=self.get_cycles_per_exec_quantile(q=0.75),
        )
