import numpy as np

from counted_float._core.counting.models import MyBaseModel, Quantiles


class SingleRunResult(MyBaseModel):
    """Result of a single run of our micro-benchmark_runs for a give # of operations."""

    n_operations: int
    t_nsecs: float

    def nsecs_per_op(self) -> float:
        return self.t_nsecs / self.n_operations


class MicroBenchmarkResult(MyBaseModel):
    """Results of all runs in the micro-benchmark_runs (warmup_runs + actual benchmark_runs runs)."""

    warmup_runs: list[SingleRunResult]
    benchmark_runs: list[SingleRunResult]

    def get_nsec_per_op_quantile(self, q: float) -> float:
        """Returns a specific quantile of all results in the 'benchmark_runs' category expressed as nsec/op."""
        return float(np.quantile([el.nsecs_per_op() for el in self.benchmark_runs], q))

    def summary_stats(self) -> Quantiles:
        return Quantiles(
            q25=self.get_nsec_per_op_quantile(q=0.25),
            q50=self.get_nsec_per_op_quantile(q=0.50),
            q75=self.get_nsec_per_op_quantile(q=0.75),
        )
