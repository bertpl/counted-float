import math

import numpy as np

from counted_float._core.compatibility import is_numba_installed, numba
from counted_float._core.models import (
    BenchmarkSettings,
    FlopsBenchmarkResults_V2,
    FlopsBenchmarkType,
    FlopType,
    Quantiles,
    SystemInfo,
)

from ._array_generator import ArrayGenerator
from ._flops_micro_benchmark import FlopsMicroBenchmark

FBT = FlopsBenchmarkType


class FlopsBenchmarkSuite:
    # -------------------------------------------------------------------------
    #  Main API
    # -------------------------------------------------------------------------
    def run(
        self,
        array_size: int = 1000,
        n_runs_total: int = 30,
        n_runs_warmup: int = 10,
        n_seconds_per_run_target: float = 0.1,
    ) -> FlopsBenchmarkResults_V2:
        """
        Run entire flops benchmarking suite and return the results as a FlopsBenchmarkResults_V2 object.
        """

        # warn if needed
        if not is_numba_installed():
            print("========= WARNING =========")
            print("'numba' was not found; results of this benchmark will be wildly inaccurate & unusable.")
            print("Install this package with the numba optional dependency: 'pip install counted-float[numba]'")
            print("========= WARNING =========")

        # run actual benchmarks
        benchmarks = self.get_flops_benchmarking_suite(size=array_size)
        results_dict: dict[FlopsBenchmarkType, Quantiles] = {
            benchmark_type: benchmark.run_many(
                n_runs_total=n_runs_total,
                n_runs_warmup=n_runs_warmup,
                n_seconds_per_run_target=n_seconds_per_run_target,
            ).summary_stats_cycles_per_exec()
            for benchmark_type, benchmark in benchmarks.items()
        }

        # compute latencies per benchmark 'op' (=combination of flops)
        n_cycles_per_op = {
            benchmark_type: Quantiles(
                q25=q.q25 / array_size,
                q50=q.q50 / array_size,
                q75=q.q75 / array_size,
            )
            for benchmark_type, q in results_dict.items()
        }

        # compute estimated FLOP latencies
        addsub_avg = 0.5 * (n_cycles_per_op[FBT.ADD].q50 + n_cycles_per_op[FBT.SUB].q50)
        estimated_flop_latencies = {
            FlopType.ABS: n_cycles_per_op[FBT.ADD_ABS].q50 - n_cycles_per_op[FBT.ADD].q50,
            FlopType.MINUS: n_cycles_per_op[FBT.ADD_MINUS].q50 - n_cycles_per_op[FBT.ADD].q50,
            FlopType.COMP: n_cycles_per_op[FBT.LTE_ADDSUB].q50 - addsub_avg,
            FlopType.RND: n_cycles_per_op[FBT.ADD_ROUND].q50 - n_cycles_per_op[FBT.ADD].q50,
            FlopType.ADD: n_cycles_per_op[FBT.ADD_ADD].q50 - n_cycles_per_op[FBT.ADD].q50,
            FlopType.SUB: n_cycles_per_op[FBT.ADD_SUB].q50 - n_cycles_per_op[FBT.ADD].q50,
            FlopType.MUL: n_cycles_per_op[FBT.MUL_MUL].q50 - n_cycles_per_op[FBT.MUL].q50,
            FlopType.DIV: n_cycles_per_op[FBT.DIV_DIV].q50 - n_cycles_per_op[FBT.DIV].q50,
            FlopType.SQRT: n_cycles_per_op[FBT.ADD_SQRT].q50 - n_cycles_per_op[FBT.ADD].q50,
            FlopType.EXP2: n_cycles_per_op[FBT.ADD_LOG2_EXP2].q50 - n_cycles_per_op[FBT.ADD_LOG2].q50,
            FlopType.LOG2: n_cycles_per_op[FBT.ADD_LOG2].q50 - n_cycles_per_op[FBT.ADD].q50,
            FlopType.POW: n_cycles_per_op[FBT.POW_POW].q50 - n_cycles_per_op[FBT.POW].q50,
        }

        # put results in appropriate format
        return FlopsBenchmarkResults_V2(
            system=SystemInfo.from_system(),
            benchmark_settings=BenchmarkSettings(
                array_size=array_size,
                n_runs_total=n_runs_total,
                n_runs_warmup=n_runs_warmup,
                n_seconds_per_run_target=n_seconds_per_run_target,
            ),
            n_cycles_per_op=n_cycles_per_op,
            estimated_flop_latencies=estimated_flop_latencies,
        )

    # -------------------------------------------------------------------------
    #  Static methods
    # -------------------------------------------------------------------------
    @staticmethod
    def get_flops_benchmarking_suite(size: int) -> dict[FlopsBenchmarkType, FlopsMicroBenchmark]:
        """
        Returns a benchmark for each FlopsBenchmarkType, of requested array size.
        """

        # --- define all test functions -------------------
        @numba.njit(parallel=False)
        def f_baseline(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp + in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_minus(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = -(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_abs(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = abs(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_add(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp + in_f[i]
                    tmp = tmp + in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_sub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp + in_f[i]
                    tmp = tmp - in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_round(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = np.round(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_sqrt(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.sqrt(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log2(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.log2(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log2_exp2(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = 2.0 ** math.log2(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_pow(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp ** in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_pow_pow(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = (tmp ** in_f[i]) ** in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_sub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp - in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_sub_sub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp - in_f[i]
                    tmp = tmp - in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_mul(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp * in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_mul_mul(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp * in_f[i]
                    tmp = tmp * in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_div(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp / in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_div_div(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp / in_f[i]
                    tmp = tmp / in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_lte_addsub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray):
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    if tmp >= in_f[i]:
                        tmp = tmp - in_f[i]
                    else:
                        tmp = tmp + in_f[i]
                    out_f[i] = tmp

        # --- return in appropriate format ----------------
        return {
            key: FlopsMicroBenchmark(name=str(key), size=size, f=f, array_init=array_init)
            for key, f, array_init in [
                (FBT.BASELINE, f_baseline, ArrayGenerator.lin_range(min_value=1.0, max_value=2.0)),
                (FBT.ADD, f_add, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_MINUS, f_add_minus, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_ABS, f_add_abs, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_ADD, f_add_add, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_SUB, f_add_sub, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_ROUND, f_add_round, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_SQRT, f_add_sqrt, ArrayGenerator.lin_range(min_value=0.0, max_value=1e16)),
                (FBT.ADD_LOG2, f_add_log2, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG2_EXP2, f_add_log2_exp2, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.POW, f_pow, ArrayGenerator.log_range(min_value=0.1, max_value=10.0)),
                (FBT.POW_POW, f_pow_pow, ArrayGenerator.log_range(min_value=0.1, max_value=10.0)),
                (FBT.SUB, f_sub, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.SUB_SUB, f_sub_sub, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.MUL, f_mul, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.MUL_MUL, f_mul_mul, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.DIV, f_div, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.DIV_DIV, f_div_div, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.LTE_ADDSUB, f_lte_addsub, ArrayGenerator.lin_range(min_value=1.0, max_value=1e16)),
            ]
        }
