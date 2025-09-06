import platform

import numpy as np
import psutil

from counted_float._core.compatibility import is_numba_installed, numba
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

        # warn if needed
        if not is_numba_installed():
            print("========= WARNING =========")
            print("'numba' was not found; results of this benchmark will be wildly inaccurate & unusable.")
            print("Install this package with the numba optional dependency: 'pip install counted-float[numba]'")
            print("========= WARNING =========")

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
    def get_flops_benchmarking_suite(size: int) -> dict[FlopType | None, FlopsMicroBenchmark]:
        """
        Returns a benchmark for each FlopType + None (=baseline test), of requested array size.
        """

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
            key: FlopsMicroBenchmark(name=name, f=f, size=size)
            for key, name, f in [
                (key, key.long_name() if key else "baseline", f)
                for key, f in [
                    (None, baseline),
                    (FlopType.ABS, flop_abs),
                    (FlopType.CMP_ZERO, flop_gte_zero),
                    (FlopType.RND, flop_rnd),
                    (FlopType.MINUS, flop_minus),
                    (FlopType.EQUALS, flop_equals),
                    (FlopType.GTE, flop_gte),
                    (FlopType.LTE, flop_lte),
                    (FlopType.ADD, flop_add),
                    (FlopType.SUB, flop_sub),
                    (FlopType.MUL, flop_mul),
                    (FlopType.SQRT, flop_sqrt),
                    (FlopType.DIV, flop_div),
                    (FlopType.POW2, flop_pow2),
                    (FlopType.LOG2, flop_log2),
                    (FlopType.POW, flop_pow),
                ]
            ]
        }
