import platform

import psutil

from counted_float._core._optional_deps import requires_benchmark_deps
from counted_float._core.counting.models import (
    BenchmarkSettings,
    FlopsBenchmarkDurations,
    FlopsBenchmarkResults,
    FlopType,
    Quantiles,
    SystemInfo,
)

from ._flops_micro_benchmark import FlopsMicroBenchmark


class FlopsBenchmarkSuite:
    # -------------------------------------------------------------------------
    #  Main API
    # -------------------------------------------------------------------------
    def run(
        self,
        array_size: int = 1000,
        n_runs_total: int = 30,
        n_runs_warmup: int = 10,
        n_seconds_per_run_target: float = 0.5,
    ) -> FlopsBenchmarkResults:
        """
        Run entire flops benchmarking suite and return the results as a FlopsBenchmarkResults object.
        """

        # run actual benchmarks
        benchmarks = self.get_flops_benchmarking_suite(size=array_size)
        results_dict: dict[FlopType | None, Quantiles] = {
            flop_type: benchmark.run_many(
                n_runs_total=n_runs_total,
                n_runs_warmup=n_runs_warmup,
                n_seconds_per_run_target=n_seconds_per_run_target,
            ).summary_stats()
            for flop_type, benchmark in benchmarks.items()
        }

        # put results in appropriate format & return
        return FlopsBenchmarkResults(
            system_info=SystemInfo(
                platform_processor=platform.processor(),
                platform_machine=platform.machine(),
                platform_system=platform.system(),
                platform_release=platform.release(),
                platform_python_version=platform.python_version(),
                platform_python_implementation=platform.python_implementation(),
                platform_python_compiler=platform.python_compiler(),
                psutil_cpu_count_logical=psutil.cpu_count(logical=True),
                psutil_cpu_count_physical=psutil.cpu_count(logical=False),
            ),
            benchmark_settings=BenchmarkSettings(
                array_size=array_size,
                n_runs_total=n_runs_total,
                n_runs_warmup=n_runs_warmup,
                n_seconds_per_run_target=n_seconds_per_run_target,
            ),
            results_ns=FlopsBenchmarkDurations(
                baseline=results_dict[None],
                flops={flop_type: results_dict[flop_type] for flop_type in FlopType},
            ),
        )

    # -------------------------------------------------------------------------
    #  Static methods
    # -------------------------------------------------------------------------
    @staticmethod
    @requires_benchmark_deps
    def get_flops_benchmarking_suite(size: int) -> dict[FlopType | None, FlopsMicroBenchmark]:
        """
        Returns a benchmark for each FlopType + None (=baseline test), of requested array size.
        """

        # --- late import of optional dependencies --------
        import numba
        import numpy as np

        # --- define all test functions -------------------
        @numba.njit(parallel=False)
        def baseline(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            """baseline benchmark to measure the overhead of the benchmarking framework + iteration"""
            for i in range(n):
                pass

        @numba.njit(parallel=False)
        def flop_abs(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = abs(in_f1[i])

        @numba.njit(parallel=False)
        def flop_minus(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = -in_f1[i]

        @numba.njit(parallel=False)
        def flop_equals(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_i[i] = in_f1[i] == in_f2[i]  # assign to integer output, to avoid unnecessary conversion overhead

        @numba.njit(parallel=False)
        def flop_gte(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_i[i] = in_f1[i] >= in_f2[i]  # assign to integer output, to avoid unnecessary conversion overhead

        @numba.njit(parallel=False)
        def flop_lte(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_i[i] = in_f1[i] <= in_f2[i]  # assign to integer output, to avoid unnecessary conversion overhead

        @numba.njit(parallel=False)
        def flop_gte_zero(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_i[i] = in_f1[i] >= 0.0  # assign to integer output, to avoid unnecessary conversion overhead

        @numba.njit(parallel=False)
        def flop_rnd(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_i[i] = np.ceil(in_f1[i])

        @numba.njit(parallel=False)
        def flop_add(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = in_f1[i] + in_f2[i]

        @numba.njit(parallel=False)
        def flop_sub(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = in_f1[i] - in_f2[i]

        @numba.njit(parallel=False)
        def flop_mul(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = in_f1[i] * in_f2[i]

        @numba.njit(parallel=False)
        def flop_div(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = in_f1[i] / in_f2[i]

        @numba.njit(parallel=False)
        def flop_sqrt(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = np.sqrt(in_f1[i])

        @numba.njit(parallel=False)
        def flop_pow2(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = 2 ** in_f1[i]

        @numba.njit(parallel=False)
        def flop_log2(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = np.log2(in_f1[i])

        @numba.njit(parallel=False)
        def flop_pow(n: int, in_f1: np.ndarray, in_f2: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for i in range(n):
                out_f[i] = in_f1[i] ** in_f2[i]

        # --- return in appropriate format ----------------
        return {
            None: FlopsMicroBenchmark(name="baseline", f=baseline, size=size),
            FlopType.ABS: FlopsMicroBenchmark(name="c=abs(a)", f=flop_abs, size=size),
            FlopType.CMP_ZERO: FlopsMicroBenchmark(name="c=(a>=0)", f=flop_gte_zero, size=size),
            FlopType.RND: FlopsMicroBenchmark(name="c=ceil(a)", f=flop_rnd, size=size),
            FlopType.MINUS: FlopsMicroBenchmark(name="c=-a", f=flop_minus, size=size),
            FlopType.EQUALS: FlopsMicroBenchmark(name="c=(a==b)", f=flop_equals, size=size),
            FlopType.GTE: FlopsMicroBenchmark(name="c=(a>=b)", f=flop_gte, size=size),
            FlopType.LTE: FlopsMicroBenchmark(name="c=(a<=b)", f=flop_lte, size=size),
            FlopType.ADD: FlopsMicroBenchmark(name="c=a+b", f=flop_add, size=size),
            FlopType.SUB: FlopsMicroBenchmark(name="c=a-b", f=flop_sub, size=size),
            FlopType.MUL: FlopsMicroBenchmark(name="c=a*b", f=flop_mul, size=size),
            FlopType.SQRT: FlopsMicroBenchmark(name="c=sqrt(a)", f=flop_sqrt, size=size),
            FlopType.DIV: FlopsMicroBenchmark(name="c=a/b", f=flop_div, size=size),
            FlopType.POW2: FlopsMicroBenchmark(name="c=2**a", f=flop_pow2, size=size),
            FlopType.LOG2: FlopsMicroBenchmark(name="c=log2(a)", f=flop_log2, size=size),
            FlopType.POW: FlopsMicroBenchmark(name="c=a^b", f=flop_pow, size=size),
        }
