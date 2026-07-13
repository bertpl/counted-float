import math
import sys
from importlib.metadata import version

import numpy as np

from counted_float._core.benchmarking.micro import InterleavedBenchmarkRunner
from counted_float._core.compatibility import is_numba_installed, numba
from counted_float._core.models import (
    BenchmarkSettings,
    FlopsBenchmarkResults,
    FlopsBenchmarkType,
    FlopType,
    Quantiles,
    SystemInfo,
)

from ._array_generator import ArrayGenerator
from ._flops_micro_benchmark import FlopsMicroBenchmark

FBT = FlopsBenchmarkType


class FlopsBenchmarkSuite:
    # differencing noisy per-kernel statistics can yield estimates <= 0 for cheap ops
    # (ABS, MINUS, COMP) on a loaded machine; latencies are floored to this fraction of
    # the measured ADD cost — well below any plausible genuine latency (the cheapest
    # measured ops sit around 0.3-1x ADD), so it only ever binds on noise artifacts.
    # The spec-sheet path applies its own floor via Latency.consensus().
    MIN_LATENCY_ADD_FRACTION = 0.1

    # -------------------------------------------------------------------------
    #  Main API
    # -------------------------------------------------------------------------
    def run(
        self,
        array_size: int = 1000,
        t_slice_target_ms: float = 20.0,
        n_rounds_measure: int = 200,
        n_rounds_warmup: int = 3,
        seed: int | None = None,
    ) -> FlopsBenchmarkResults:
        """Run entire flops benchmarking suite and return the results as a FlopsBenchmarkResults object.

        All benchmarks run round-robin interleaved (see InterleavedBenchmarkRunner): each
        measurement round runs every benchmark for one ~t_slice_target_ms slice, in an
        order re-shuffled per round, so machine-wide disturbances cancel in the pairwise
        differences below.  Per-benchmark latency is estimated from the q10 of its
        recorded slices: contention is strictly additive noise, so a low quantile
        approaches the uncontended latency (q10 rather than the minimum, so a single
        too-low CPU-frequency sample cannot select the worst conversion outlier).
        An optional seed makes input pools and round shuffles reproducible.
        """
        # warn if needed
        if not is_numba_installed():
            print("========= WARNING =========")
            print("'numba' was not found; results of this benchmark will be wildly inaccurate & unusable.")
            print("Install this package with the numba optional dependency: 'pip install counted-float[numba]'")
            print("========= WARNING =========")

        print()
        print(f"Running FLOPS benchmarks using counted-float {version('counted-float')} ...")
        print(
            f"(Expected duration: "
            f"~{(n_rounds_measure + n_rounds_warmup) * len(FlopsBenchmarkType) * t_slice_target_ms / 1000:.0f}"
            f" seconds, plus jit compilation & calibration)"
        )
        print()

        # run actual benchmarks (round-robin interleaved)
        benchmarks = self.get_flops_benchmarking_suite(size=array_size)
        runner = InterleavedBenchmarkRunner(
            benchmarks=benchmarks,
            t_slice_target_ms=t_slice_target_ms,
            n_rounds_measure=n_rounds_measure,
            n_rounds_warmup=n_rounds_warmup,
            seed=seed,
        )
        raw_results = runner.run()

        # compute latencies per benchmark 'op' (=combination of flops)
        n_cycles_per_op = {
            benchmark_type: Quantiles(
                q10=result.get_cycles_per_exec_quantile(q=0.10) / array_size,
                q25=result.get_cycles_per_exec_quantile(q=0.25) / array_size,
                q50=result.get_cycles_per_exec_quantile(q=0.50) / array_size,
                q75=result.get_cycles_per_exec_quantile(q=0.75) / array_size,
            )
            for benchmark_type, result in raw_results.items()
        }

        # compute estimated FLOP latencies (from the q10 of each benchmark's slices)
        q10s: dict[FlopsBenchmarkType, float] = {
            benchmark_type: result.get_cycles_per_exec_quantile(q=0.10) / array_size
            for benchmark_type, result in raw_results.items()
        }
        addsub_avg = 0.5 * (q10s[FBT.ADD] + q10s[FBT.SUB])
        estimated_flop_latencies = {
            FlopType.ABS: q10s[FBT.ADD_ABS] - q10s[FBT.ADD],
            FlopType.MINUS: q10s[FBT.ADD_MINUS] - q10s[FBT.ADD],
            FlopType.COMP: q10s[FBT.LTE_ADDSUB] - addsub_avg,
            FlopType.RND: q10s[FBT.ADD_ROUND] - q10s[FBT.ADD],
            FlopType.ADD: q10s[FBT.ADD_ADD] - q10s[FBT.ADD],
            FlopType.SUB: q10s[FBT.ADD_SUB] - q10s[FBT.ADD],
            FlopType.MUL: q10s[FBT.MUL_MUL] - q10s[FBT.MUL],
            FlopType.DIV: q10s[FBT.DIV_DIV] - q10s[FBT.DIV],
            FlopType.SQRT: q10s[FBT.ADD_SQRT] - q10s[FBT.ADD],
            FlopType.CBRT: q10s[FBT.ADD_CBRT] - q10s[FBT.ADD],
            FlopType.EXP: q10s[FBT.ADD_LOG_EXP] - q10s[FBT.ADD_LOG],
            FlopType.EXP2: q10s[FBT.ADD_LOG2_EXP2] - q10s[FBT.ADD_LOG2],
            FlopType.EXP10: q10s[FBT.ADD_LOG10_EXP10] - q10s[FBT.ADD_LOG10],
            FlopType.LOG: q10s[FBT.ADD_LOG] - q10s[FBT.ADD],
            FlopType.LOG2: q10s[FBT.ADD_LOG2] - q10s[FBT.ADD],
            FlopType.LOG10: q10s[FBT.ADD_LOG10] - q10s[FBT.ADD],
            FlopType.POW: q10s[FBT.POW_POW] - q10s[FBT.POW],
            FlopType.SIN: q10s[FBT.ADD_SIN] - q10s[FBT.ADD],
            FlopType.COS: q10s[FBT.ADD_COS] - q10s[FBT.ADD],
            FlopType.TAN: q10s[FBT.ADD_TAN] - q10s[FBT.ADD],
            FlopType.ASIN: q10s[FBT.ADD_SIN_ASIN] - q10s[FBT.ADD_SIN],
            FlopType.ACOS: q10s[FBT.ADD_SIN_ACOS] - q10s[FBT.ADD_SIN],
            FlopType.ATAN: q10s[FBT.ADD_ATAN] - q10s[FBT.ADD],
            FlopType.ATAN2: q10s[FBT.ADD_ATAN2] - q10s[FBT.ADD],
            FlopType.HYPOT: q10s[FBT.ADD_HYPOT] - q10s[FBT.ADD],
            FlopType.LOG1P: q10s[FBT.ADD_LOG1P] - q10s[FBT.ADD],
            FlopType.EXPM1: q10s[FBT.ADD_LOG1P_EXPM1] - q10s[FBT.ADD_LOG1P],
            FlopType.FMOD: q10s[FBT.ADD_FMOD] - q10s[FBT.ADD],
            FlopType.TANH: q10s[FBT.ADD_TANH] - q10s[FBT.ADD],
            FlopType.ASINH: q10s[FBT.ADD_ASINH] - q10s[FBT.ADD],
            FlopType.SINH: q10s[FBT.ADD_ASINH_SINH] - q10s[FBT.ADD_ASINH],
            FlopType.ACOSH: q10s[FBT.ADD_ACOSH] - q10s[FBT.ADD],
            FlopType.COSH: q10s[FBT.ADD_ACOSH_COSH] - q10s[FBT.ADD_ACOSH],
            FlopType.ATANH: q10s[FBT.ADD_HALFSIN_ATANH] - q10s[FBT.ADD_HALFSIN],
        }
        estimated_flop_latencies = self.floor_latencies(estimated_flop_latencies)

        # put results in appropriate format
        return FlopsBenchmarkResults(
            system=SystemInfo.from_system(),
            benchmark_settings=BenchmarkSettings(
                array_size=array_size,
                t_slice_target_ms=t_slice_target_ms,
                n_rounds_measure=n_rounds_measure,
                n_rounds_warmup=n_rounds_warmup,
                input_pool_size=FlopsMicroBenchmark.INPUT_POOL_SIZE,
                order_shuffled=True,
            ),
            n_cycles_per_op=n_cycles_per_op,
            estimated_flop_latencies=estimated_flop_latencies,
        )

    # -------------------------------------------------------------------------
    #  Static methods
    # -------------------------------------------------------------------------
    @classmethod
    def floor_latencies(cls, latencies: dict[FlopType, float]) -> dict[FlopType, float]:
        """Clamp estimated per-flop latencies to a small positive floor.

        The floor is MIN_LATENCY_ADD_FRACTION times the estimated ADD latency, so a noisy
        run can never produce zero, negative, or otherwise invalid weights downstream
        (a negative weight reaching a geometric mean would go complex).  If even the ADD
        estimate is non-positive, the run is garbage anyway; the floor then degrades to
        the smallest positive float so results remain representable.
        """
        floor = cls.MIN_LATENCY_ADD_FRACTION * max(latencies[FlopType.ADD], sys.float_info.min)
        return {flop_type: max(latency, floor) for flop_type, latency in latencies.items()}

    @staticmethod
    def get_flops_benchmarking_suite(size: int) -> dict[FlopsBenchmarkType, FlopsMicroBenchmark]:  # noqa: C901 -- flat registry of per-flop-type jit kernels
        """Returns a benchmark for each FlopsBenchmarkType, of requested array size."""

        # --- define all test functions -------------------
        @numba.njit(parallel=False)
        def f_baseline(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp + in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_minus(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = -(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_abs(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = abs(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_add(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp + in_f[i]
                    tmp = tmp + in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_sub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp + in_f[i]
                    tmp = tmp - in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_round(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = np.round(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_sqrt(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.sqrt(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_cbrt(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = np.cbrt(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.log(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log_exp(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.exp(math.log(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log2(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = np.log2(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log2_exp2(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = np.exp2(np.log2(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log10(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = np.log10(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log10_exp10(
            n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray
        ) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = 10 ** np.log10(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_sin(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.sin(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_cos(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.cos(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_tan(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.tan(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_sin_asin(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            # sin bounds the argument to [-1, 1] so asin stays in-domain in the dependent chain;
            # subtract add_sin to isolate the asin cost
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.asin(math.sin(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_sin_acos(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            # sin bounds the argument to [-1, 1] for acos; subtract add_sin to isolate the acos cost
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.acos(math.sin(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_atan(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.atan(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_atan2(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.atan2(tmp + in_f[i], in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_hypot(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.hypot(tmp + in_f[i], in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log1p(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.log1p(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_log1p_expm1(
            n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray
        ) -> None:
            # log1p is the inverse of expm1, keeping the chain bounded (mirrors add_log_exp for exp);
            # subtract add_log1p to isolate the expm1 cost
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.expm1(math.log1p(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_fmod(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            # np.fmod: numba lacks math.fmod; the positive divisor range avoids the fmod(x, 0) domain error
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = np.fmod(tmp + in_f[i], in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_tanh(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.tanh(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_asinh(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.asinh(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_asinh_sinh(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            # asinh is the inverse of sinh, keeping the chain bounded (mirrors add_log_exp for exp);
            # subtract add_asinh to isolate the sinh cost
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.sinh(math.asinh(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_acosh(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            # the large positive range keeps the argument >= 1 (acosh's domain)
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.acosh(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_acosh_cosh(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            # acosh is the inverse of cosh (for x >= 1), keeping the chain bounded; subtract add_acosh
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.cosh(math.acosh(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_halfsin(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            # baseline for atanh: 0.5*sin keeps the argument in [-0.5, 0.5], safely inside atanh's (-1, 1) domain
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = 0.5 * math.sin(tmp + in_f[i])
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_add_halfsin_atanh(
            n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray
        ) -> None:
            # 0.5*sin bounds the argument well inside (-1, 1); subtract add_halfsin to isolate the atanh cost
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = math.atanh(0.5 * math.sin(tmp + in_f[i]))
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_pow(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp ** in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_pow_pow(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = (tmp ** in_f[i]) ** in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_sub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp - in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_sub_sub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp - in_f[i]
                    tmp = tmp - in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_mul(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp * in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_mul_mul(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp * in_f[i]
                    tmp = tmp * in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_div(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp / in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_div_div(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    tmp = tmp / in_f[i]
                    tmp = tmp / in_f[i]
                    out_f[i] = tmp

        @numba.njit(parallel=False)
        def f_lte_addsub(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
            for _ in range(n_executions):
                tmp = math.e
                for i in range(n):
                    if tmp >= in_f[i]:  # noqa: SIM108 -- timed kernel: keep the branchy shape being measured
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
                (FBT.ADD_CBRT, f_add_cbrt, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_LOG, f_add_log, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG_EXP, f_add_log_exp, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG2, f_add_log2, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG2_EXP2, f_add_log2_exp2, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG10, f_add_log10, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG10_EXP10, f_add_log10_exp10, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_SIN, f_add_sin, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_COS, f_add_cos, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_TAN, f_add_tan, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_SIN_ASIN, f_add_sin_asin, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_SIN_ACOS, f_add_sin_acos, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_ATAN, f_add_atan, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_ATAN2, f_add_atan2, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_HYPOT, f_add_hypot, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_LOG1P, f_add_log1p, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG1P_EXPM1, f_add_log1p_expm1, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_FMOD, f_add_fmod, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                # tanh saturates to +/-1 via a cheap early-return for |arg| > ~20, so (unlike the
                # periodic sin/cos/tan) keep inputs small to measure its real, exp-based cost
                (FBT.ADD_TANH, f_add_tanh, ArrayGenerator.lin_range(min_value=-5.0, max_value=5.0)),
                (FBT.ADD_ASINH, f_add_asinh, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_ASINH_SINH, f_add_asinh_sinh, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_ACOSH, f_add_acosh, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_ACOSH_COSH, f_add_acosh_cosh, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_HALFSIN, f_add_halfsin, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_HALFSIN_ATANH, f_add_halfsin_atanh, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
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
