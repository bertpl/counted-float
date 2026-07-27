import sys
import warnings
from importlib.metadata import version

from counted_float._core.benchmarking._output import console
from counted_float._core.benchmarking.micro import InterleavedBenchmarkRunner
from counted_float._core.compatibility import is_numba_importable
from counted_float._core.models import (
    BenchmarkSettings,
    FlopsBenchmarkResults,
    FlopsBenchmarkType,
    FlopType,
    Quantiles,
    SystemInfo,
)
from counted_float._core.utils import get_cpu_frequency_mhz_current

from ._array_generator import ArrayGenerator
from ._flops_micro_benchmark import FlopsMicroBenchmark

FBT = FlopsBenchmarkType


class FlopsBenchmarkSuite:
    # differencing noisy per-probe statistics can yield estimates <= 0 for cheap ops
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

        Progress goes to the shared benchmark console (silenced via output_quiet); the
        missing-numba RuntimeWarning is emitted regardless of console verbosity.
        """
        # a missing numba yields unusable results -- always surface it (regardless of console
        # verbosity) through the warnings machinery, so callers can filter or escalate it
        if not is_numba_importable():
            warnings.warn(
                "'numba' is not installed; FLOPS benchmark results will be wildly inaccurate "
                "and unusable. Install the optional dependency with pip install 'counted-float[numba]'.",
                RuntimeWarning,
                stacklevel=2,
            )

        # a missing CPU-frequency reading makes the ns->cycles conversion fall back to a nominal
        # 1 GHz (see convert_nsecs_to_cycles), so the reported per-op "cycle" figures are then really
        # nanoseconds -- surface that; only the derived flop-weight ratios (scale-invariant) stay valid
        if get_cpu_frequency_mhz_current() is None:
            warnings.warn(
                "CPU frequency is unavailable; benchmark per-op figures are reported in nanoseconds, "
                "not cycles. The derived flop weights (ratios) are unaffected.",
                RuntimeWarning,
                stacklevel=2,
            )

        console.print()
        console.print(f"Running FLOPS benchmarks using counted-float {version('counted-float')} ...")
        console.print(
            f"(Expected duration: "
            f"~{(n_rounds_measure + n_rounds_warmup) * len(FlopsBenchmarkType) * t_slice_target_ms / 1000:.0f}"
            f" seconds, plus jit compilation & calibration)"
        )
        console.print()

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
            FlopType.COPYSIGN: q10s[FBT.ADD_COPYSIGN] - q10s[FBT.ADD],
            FlopType.COMP: q10s[FBT.LTE_ADDSUB] - addsub_avg,
            FlopType.RND: q10s[FBT.ADD_ROUND] - q10s[FBT.ADD],
            FlopType.ADD: q10s[FBT.ADD_ADD] - q10s[FBT.ADD],
            FlopType.SUB: q10s[FBT.ADD_SUB] - q10s[FBT.ADD],
            FlopType.MUL: q10s[FBT.MUL_MUL] - q10s[FBT.MUL],
            FlopType.DIV: q10s[FBT.DIV_DIV] - q10s[FBT.DIV],
            FlopType.FMA: q10s[FBT.FMA_FMA] - q10s[FBT.FMA],
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
            # per-extra-coordinate cost of the overflow-safe (scaled) form: the arity-2 probe cancels
            # the shared scaling + sqrt + chained coordinate, so dividing the arity-8 minus arity-2 gap
            # by the 6 extra coordinates isolates the slope. The scaled arity-2 form reproduces the libm
            # HYPOT above, so base and slope are one algorithm.
            FlopType.HYPOT_XARG: (q10s[FBT.ADD_HYPOT_SCALED8] - q10s[FBT.ADD_HYPOT_SCALED2]) / 6,
            # dist carries its own 2-D offset (it counts a subtraction per coordinate that hypot does not)
            FlopType.DIST: q10s[FBT.ADD_DIST2] - q10s[FBT.ADD],
            FlopType.DIST_XARG: (q10s[FBT.ADD_DIST8] - q10s[FBT.ADD_DIST2]) / 6,
            # sumprod mirrors the arity scheme: the 2-element base includes the close-out, and the
            # arity-8 minus arity-2 gap over the 6 extra elements isolates the per-element slope
            FlopType.SUMPROD: q10s[FBT.ADD_SUMPROD2] - q10s[FBT.ADD],
            FlopType.SUMPROD_XELEM: (q10s[FBT.ADD_SUMPROD8] - q10s[FBT.ADD_SUMPROD2]) / 6,
            FlopType.LOG1P: q10s[FBT.ADD_LOG1P] - q10s[FBT.ADD],
            FlopType.EXPM1: q10s[FBT.ADD_LOG1P_EXPM1] - q10s[FBT.ADD_LOG1P],
            FlopType.FMOD: q10s[FBT.ADD_FMOD] - q10s[FBT.ADD],
            FlopType.REMAINDER: q10s[FBT.ADD_REMAINDER] - q10s[FBT.ADD],
            FlopType.TANH: q10s[FBT.ADD_TANH] - q10s[FBT.ADD],
            FlopType.ASINH: q10s[FBT.ADD_ASINH] - q10s[FBT.ADD],
            FlopType.SINH: q10s[FBT.ADD_ASINH_SINH] - q10s[FBT.ADD_ASINH],
            FlopType.ACOSH: q10s[FBT.ADD_ACOSH] - q10s[FBT.ADD],
            FlopType.COSH: q10s[FBT.ADD_ACOSH_COSH] - q10s[FBT.ADD_ACOSH],
            FlopType.ATANH: q10s[FBT.ADD_HALFSIN_ATANH] - q10s[FBT.ADD_HALFSIN],
            # gamma/lgamma subtract the shared sin-bounding baseline (not ADD): it cancels the
            # sin + shift the two probes carry to keep the chain finite, leaving the function cost
            FlopType.GAMMA: q10s[FBT.ADD_GAMMABASE_GAMMA] - q10s[FBT.ADD_GAMMABASE],
            FlopType.LGAMMA: q10s[FBT.ADD_GAMMABASE_LGAMMA] - q10s[FBT.ADD_GAMMABASE],
            FlopType.ERF: q10s[FBT.ADD_ERF] - q10s[FBT.ADD],
            FlopType.ERFC: q10s[FBT.ADD_ERFC] - q10s[FBT.ADD],
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

    # The arity probes read a window of elements behind the current index via negative offsets
    # (the widest, the arity-8 sumprod form, reaches 15 back), so arrays below this size would
    # index out of bounds -- an IndexError in pure Python, a silent out-of-bounds read under
    # numba's default unchecked indexing.
    MIN_ARRAY_SIZE = 16

    @staticmethod
    def get_flops_benchmarking_suite(size: int) -> dict[FlopsBenchmarkType, FlopsMicroBenchmark]:
        """Returns a benchmark for each FlopsBenchmarkType, of requested array size.

        Raises:
            ValueError: If `size` is below MIN_ARRAY_SIZE (the arity probes' look-behind window).
        """
        if size < FlopsBenchmarkSuite.MIN_ARRAY_SIZE:
            raise ValueError(
                f"array_size must be >= {FlopsBenchmarkSuite.MIN_ARRAY_SIZE}: the arity probes read up to "
                f"{FlopsBenchmarkSuite.MIN_ARRAY_SIZE - 1} elements behind the current index"
            )
        # imported here rather than at module level: the probes bind libm ctypes functions when
        # imported, which fails loudly on platforms without a locatable C math library -- that
        # failure belongs to running the flops benchmark, not to importing the benchmarking API
        from . import _flops_probes as probes

        # --- assemble the registry -----------------------
        return {
            key: FlopsMicroBenchmark(name=str(key), size=size, f=f, array_init=array_init)
            for key, f, array_init in [
                (FBT.BASELINE, probes.f_baseline, ArrayGenerator.lin_range(min_value=1.0, max_value=2.0)),
                (FBT.ADD, probes.f_add, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_MINUS, probes.f_add_minus, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_ABS, probes.f_add_abs, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (
                    FBT.ADD_COPYSIGN,
                    probes.f_add_copysign,
                    ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16),
                ),
                (FBT.ADD_ADD, probes.f_add_add, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_SUB, probes.f_add_sub, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_ROUND, probes.f_add_round, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.ADD_SQRT, probes.f_add_sqrt, ArrayGenerator.lin_range(min_value=0.0, max_value=1e16)),
                (FBT.ADD_CBRT, probes.f_add_cbrt, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                # log family (and the chained exp partners, which must share the range so the log
                # cost cancels): measured flat across 2..1000 vs 1e10..1e100, so the range is not
                # load-bearing -- kept as registered
                (FBT.ADD_LOG, probes.f_add_log, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG_EXP, probes.f_add_log_exp, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG2, probes.f_add_log2, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG2_EXP2, probes.f_add_log2_exp2, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (FBT.ADD_LOG10, probes.f_add_log10, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (
                    FBT.ADD_LOG10_EXP10,
                    probes.f_add_log10_exp10,
                    ArrayGenerator.lin_range(min_value=1e10, max_value=1e100),
                ),
                # sin/cos/tan: +/-100 targets the flat general-case plateau (+/-16 .. +/-1e4 measured
                # flat) -- +/-2 would underprice (sub-reduction regime), +/-1e6 would overprice
                # (huge-argument reduction regime, ~5-7% above the plateau).  The asin/acos chains
                # share sin's range so the sin cost cancels in their subtraction
                (FBT.ADD_SIN, probes.f_add_sin, ArrayGenerator.lin_range(min_value=-100.0, max_value=100.0)),
                (FBT.ADD_COS, probes.f_add_cos, ArrayGenerator.lin_range(min_value=-100.0, max_value=100.0)),
                (FBT.ADD_TAN, probes.f_add_tan, ArrayGenerator.lin_range(min_value=-100.0, max_value=100.0)),
                (
                    FBT.ADD_SIN_ASIN,
                    probes.f_add_sin_asin,
                    ArrayGenerator.lin_range(min_value=-100.0, max_value=100.0),
                ),
                (
                    FBT.ADD_SIN_ACOS,
                    probes.f_add_sin_acos,
                    ArrayGenerator.lin_range(min_value=-100.0, max_value=100.0),
                ),
                # atan/atan2: +/-100 keeps most magnitudes above 1 (atan's reciprocal branch,
                # the general case) while avoiding the huge-argument regime, where glibc's atan
                # gets ~10% *cheaper* (Apple libm is flat there; atan2 is flat on both) -- and it
                # keeps the whole trig family on one range.
                (FBT.ADD_ATAN, probes.f_add_atan, ArrayGenerator.lin_range(min_value=-100.0, max_value=100.0)),
                (FBT.ADD_ATAN2, probes.f_add_atan2, ArrayGenerator.lin_range(min_value=-100.0, max_value=100.0)),
                (FBT.ADD_HYPOT, probes.f_add_hypot, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (
                    FBT.ADD_HYPOT_SCALED2,
                    probes.f_add_hypot_scaled2,
                    ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6),
                ),
                (
                    FBT.ADD_HYPOT_SCALED8,
                    probes.f_add_hypot_scaled8,
                    ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6),
                ),
                (FBT.ADD_DIST2, probes.f_add_dist2, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (FBT.ADD_DIST8, probes.f_add_dist8, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                # sumprod: compensated mul/add/fma arithmetic has no input-dependent regimes, so the
                # range is not load-bearing; +/-1 keeps the fed-back chain bounded (it grows by at
                # most the number of elements per iteration)
                (FBT.ADD_SUMPROD2, probes.f_add_sumprod2, ArrayGenerator.lin_range(min_value=-1.0, max_value=1.0)),
                (FBT.ADD_SUMPROD8, probes.f_add_sumprod8, ArrayGenerator.lin_range(min_value=-1.0, max_value=1.0)),
                (FBT.ADD_LOG1P, probes.f_add_log1p, ArrayGenerator.lin_range(min_value=1e10, max_value=1e100)),
                (
                    FBT.ADD_LOG1P_EXPM1,
                    probes.f_add_log1p_expm1,
                    ArrayGenerator.lin_range(min_value=1e10, max_value=1e100),
                ),
                (FBT.ADD_FMOD, probes.f_add_fmod, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (
                    FBT.ADD_REMAINDER,
                    probes.f_add_remainder,
                    ArrayGenerator.log_range(min_value=1e-16, max_value=1e16),
                ),
                # tanh saturates to +/-1 via a cheap early-return for |arg| > ~20, so (unlike the
                # periodic sin/cos/tan) keep inputs small to measure its real, exp-based cost
                (FBT.ADD_TANH, probes.f_add_tanh, ArrayGenerator.lin_range(min_value=-5.0, max_value=5.0)),
                # asinh/acosh: moderate arguments price the general case -- huge arguments
                # (1e10..1e100) would land in the asymptotic asinh(x) ~ log(2x) shortcut regime,
                # measured ~35-40% cheaper than the flat 0.5..1e6 plateau.  The sinh/cosh chains
                # share the range so the asinh/acosh cost cancels in their subtraction (their own
                # arguments are the moderate asinh/acosh outputs).  acosh's positive range also
                # keeps its argument >= 1 (acosh's domain)
                (FBT.ADD_ASINH, probes.f_add_asinh, ArrayGenerator.lin_range(min_value=0.5, max_value=3.0)),
                (
                    FBT.ADD_ASINH_SINH,
                    probes.f_add_asinh_sinh,
                    ArrayGenerator.lin_range(min_value=0.5, max_value=3.0),
                ),
                (FBT.ADD_ACOSH, probes.f_add_acosh, ArrayGenerator.lin_range(min_value=2.0, max_value=10.0)),
                (
                    FBT.ADD_ACOSH_COSH,
                    probes.f_add_acosh_cosh,
                    ArrayGenerator.lin_range(min_value=2.0, max_value=10.0),
                ),
                (FBT.ADD_HALFSIN, probes.f_add_halfsin, ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6)),
                (
                    FBT.ADD_HALFSIN_ATANH,
                    probes.f_add_halfsin_atanh,
                    ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6),
                ),
                # gamma/lgamma: the sin bound makes these probes insensitive to the input range (it
                # only perturbs the sin argument), so any finite range works -- match the halfsin span
                (
                    FBT.ADD_GAMMABASE,
                    probes.f_add_gammabase,
                    ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6),
                ),
                (
                    FBT.ADD_GAMMABASE_GAMMA,
                    probes.f_add_gammabase_gamma,
                    ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6),
                ),
                (
                    FBT.ADD_GAMMABASE_LGAMMA,
                    probes.f_add_gammabase_lgamma,
                    ArrayGenerator.lin_range(min_value=-1e6, max_value=1e6),
                ),
                # erf/erfc saturate to constants at the tails via cheap fast-paths (erf: |x|>~6; erfc:
                # x>~27), so -- like tanh -- keep the argument small to measure their real, polynomial cost
                (FBT.ADD_ERF, probes.f_add_erf, ArrayGenerator.lin_range(min_value=0.5, max_value=2.0)),
                (FBT.ADD_ERFC, probes.f_add_erfc, ArrayGenerator.lin_range(min_value=0.5, max_value=2.5)),
                # pow: measured flat (log 0.5..2 vs log 0.1..10) -- kept; the geomean-1 log range
                # also keeps the chained tmp ** x bounded
                (FBT.POW, probes.f_pow, ArrayGenerator.log_range(min_value=0.1, max_value=10.0)),
                (FBT.POW_POW, probes.f_pow_pow, ArrayGenerator.log_range(min_value=0.1, max_value=10.0)),
                (FBT.SUB, probes.f_sub, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.SUB_SUB, probes.f_sub_sub, ArrayGenerator.lin_range(min_value=-1e16, max_value=1e16)),
                (FBT.MUL, probes.f_mul, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.MUL_MUL, probes.f_mul_mul, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.DIV, probes.f_div, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.DIV_DIV, probes.f_div_div, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.FMA, probes.f_fma, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.FMA_FMA, probes.f_fma_fma, ArrayGenerator.log_range(min_value=1e-16, max_value=1e16)),
                (FBT.LTE_ADDSUB, probes.f_lte_addsub, ArrayGenerator.lin_range(min_value=1.0, max_value=1e16)),
            ]
        }
