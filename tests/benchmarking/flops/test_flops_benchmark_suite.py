import math
import re

import numpy as np
import pytest

from counted_float._core.benchmarking.flops import FlopsBenchmarkSuite, FlopsMicroBenchmark
from counted_float._core.benchmarking.flops import _flops_kernels as kernels
from counted_float._core.compatibility import is_numba_installed
from counted_float._core.models import FlopsBenchmarkResults, FlopsBenchmarkType, FlopType, FlopWeights


def test_flops_benchmarking_suite_get():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    benchmarks = suite.get_flops_benchmarking_suite(size=12345)

    # --- assert ------------------------------------------
    assert all(fbt in benchmarks for fbt in FlopsBenchmarkType)
    assert all(isinstance(v, FlopsMicroBenchmark) for v in benchmarks.values())
    assert all(v.size == 12345 for v in benchmarks.values())


def test_flops_benchmarking_suite_run():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    result = suite.run(
        array_size=10,
        t_slice_target_ms=0.1,
        n_rounds_measure=5,
        n_rounds_warmup=1,
        seed=42,
    )  # override defaults to keep test short

    # --- assert ------------------------------------------
    assert isinstance(result, FlopsBenchmarkResults)


@pytest.mark.skipif(not is_numba_installed(), reason="arity-slope values need real numba timings, not the shim")
def test_suite_measures_the_arity_flop_types():
    """The hypot/dist arity kernels feed HYPOT_XARG / DIST / DIST_XARG with sane, ordered latencies."""
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    result = suite.run(array_size=1000, t_slice_target_ms=2.0, n_rounds_measure=15, n_rounds_warmup=2, seed=7)
    efl = result.estimated_flop_latencies

    # --- assert ------------------------------------------
    for flop_type in (FlopType.HYPOT_XARG, FlopType.DIST, FlopType.DIST_XARG):
        assert math.isfinite(efl[flop_type]), flop_type
        assert efl[flop_type] > 0, flop_type
    # an extra coordinate is far cheaper than a whole 2-arg call (its squares overlap the sqrt path)
    assert efl[FlopType.HYPOT_XARG] < efl[FlopType.HYPOT]
    assert efl[FlopType.DIST_XARG] < efl[FlopType.DIST]


@pytest.mark.skipif(not is_numba_installed(), reason="kernel execution needs real numba, not the shim")
def test_remainder_kernel_matches_math_remainder():
    """The ctypes-bound libm call must compute exactly what math.remainder computes.

    numba has no math.remainder, so the kernel calls libm through ctypes -- this pins that the
    bound symbol is the right function (IEEE remainder, not fmod).
    """
    # --- arrange -----------------------------------------
    n = 50
    in_f = np.exp(np.linspace(np.log(1e-16), np.log(1e16), n))
    out_f, out_i = np.zeros(n), np.zeros(n, dtype=int)

    # --- act ---------------------------------------------
    kernels.f_add_remainder(1, n, in_f, out_f, out_i)

    # --- assert ------------------------------------------
    tmp = math.e
    for i in range(n):
        tmp = math.remainder(tmp + in_f[i], in_f[i])
        assert out_f[i] == tmp


@pytest.mark.skipif(not is_numba_installed(), reason="kernel execution needs real numba, not the shim")
def test_cbrt_kernel_matches_math_cbrt():
    """The ctypes-bound libm call must compute exactly what math.cbrt computes.

    The kernel calls libm through ctypes rather than through numba's np.cbrt, whose NaN/sign
    wrapper CPython's math.cbrt never executes -- this pins that the bound symbol is the right
    function, negative arguments included.
    """
    # --- arrange -----------------------------------------
    n = 50
    in_f = np.linspace(-1e16, 1e16, n)
    out_f, out_i = np.zeros(n), np.zeros(n, dtype=int)

    # --- act ---------------------------------------------
    kernels.f_add_cbrt(1, n, in_f, out_f, out_i)

    # --- assert ------------------------------------------
    tmp = math.e
    for i in range(n):
        tmp = math.cbrt(tmp + in_f[i])
        assert out_f[i] == tmp


@pytest.mark.skipif(not is_numba_installed(), reason="kernel execution needs real numba, not the shim")
@pytest.mark.parametrize("kernel", [kernels.f_add_gammabase_gamma, kernels.f_add_gammabase_lgamma])
def test_gamma_kernels_never_overflow_even_on_a_wild_input_range(kernel):
    """The sin bound must keep the gamma/lgamma chain finite regardless of the input magnitudes.

    gamma/lgamma outputs grow without bound, so a naive `f(tmp + x)` chain overflows into a run-ending
    OverflowError. The `1.5 + 0.5*sin(...)` bound is what prevents that; feeding a deliberately wild
    input range asserts the guard holds unconditionally, not just for the registered range.
    """
    # --- arrange -----------------------------------------
    rng = np.random.default_rng(0)
    in_f = rng.uniform(-1e6, 1e6, 2000)
    out_f, out_i = np.zeros(2000), np.zeros(2000, dtype=int)

    # --- act ---------------------------------------------
    kernel(50, 2000, in_f, out_f, out_i)

    # --- assert ------------------------------------------
    assert np.all(np.isfinite(out_f))


# =================================================================================================
#  FMA kernel fusion
# =================================================================================================
# fused multiply-add mnemonics, and their unfused counterparts, on aarch64 and x86-64
_FUSED = re.compile(r"\b(fmadd|fmsub|fnmadd|fnmsub|vfmadd\w*|vfmsub\w*)\b", re.IGNORECASE)
_UNFUSED_MUL_ADD = re.compile(r"\b(fmul|fadd|mulsd|addsd|vmulsd|vaddsd)\b", re.IGNORECASE)


def _kernel_assembly(benchmark: FlopsMicroBenchmark) -> str:
    """Compile a benchmark's kernel and return the assembly emitted for it."""
    # njit compiles lazily, so run the kernel once to give it a signature to report on
    in_f = benchmark.array_init.new_array(benchmark.size)
    benchmark.f(1, benchmark.size, in_f, np.zeros(benchmark.size), np.zeros(benchmark.size, dtype=int))
    return "\n".join(benchmark.f.inspect_asm().values())


@pytest.mark.skipif(not is_numba_installed(), reason="assembly inspection needs real numba, not the shim")
@pytest.mark.parametrize("benchmark_type", [FlopsBenchmarkType.FMA, FlopsBenchmarkType.FMA_FMA])
def test_fma_kernels_compile_to_fused_multiply_adds(benchmark_type: FlopsBenchmarkType):
    """Each multiply-add in the FMA kernels must collapse into one fused instruction, leaving none behind.

    This is what makes the FMA latency estimate falsifiable. A toolchain that stopped contracting would
    leave the pair measuring a separate multiply and add while still reporting the difference as an FMA
    latency, and nothing else in the suite would notice.

    Instruction counts are deliberately not asserted: LLVM's unroll factor differs per kernel and across
    versions, so a count pins a heuristic rather than the property that matters.
    """
    # --- arrange -----------------------------------------
    benchmark = FlopsBenchmarkSuite.get_flops_benchmarking_suite(size=100)[benchmark_type]

    # --- act ---------------------------------------------
    asm = _kernel_assembly(benchmark)

    # --- assert ------------------------------------------
    assert _FUSED.search(asm), "multiply-add did not fuse: this kernel measures MUL + ADD, not FMA"
    assert not _UNFUSED_MUL_ADD.search(asm), "an unfused multiply or add survived in an FMA kernel"


@pytest.mark.skipif(not is_numba_installed(), reason="assembly inspection needs real numba, not the shim")
@pytest.mark.parametrize(
    "benchmark_type",
    [FlopsBenchmarkType.ADD, FlopsBenchmarkType.ADD_ADD, FlopsBenchmarkType.MUL, FlopsBenchmarkType.MUL_MUL],
)
def test_contraction_is_scoped_to_the_fma_kernels(benchmark_type: FlopsBenchmarkType):
    """No other kernel may fuse: the ADD and MUL pairs have to measure the operation they are named for."""
    # --- arrange -----------------------------------------
    benchmark = FlopsBenchmarkSuite.get_flops_benchmarking_suite(size=100)[benchmark_type]

    # --- act ---------------------------------------------
    asm = _kernel_assembly(benchmark)

    # --- assert ------------------------------------------
    assert not _FUSED.search(asm)


# =================================================================================================
#  floor_latencies
# =================================================================================================
def _latencies(overrides: dict[FlopType, float]) -> dict[FlopType, float]:
    """Build a full latency dict with plausible defaults, then apply overrides."""
    latencies = dict.fromkeys(FlopType, 5.0)
    latencies.update(overrides)
    return latencies


def test_floor_latencies_leaves_genuine_values_untouched():
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ABS: 2.0, FlopType.POW: 150.0})

    # --- act ---------------------------------------------
    floored = FlopsBenchmarkSuite.floor_latencies(latencies)

    # --- assert ------------------------------------------
    assert floored == latencies


@pytest.mark.parametrize("bad_value", [0.0, -0.3, -100.0])
def test_floor_latencies_clamps_non_positive_values(bad_value: float):
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ABS: bad_value})

    # --- act ---------------------------------------------
    floored = FlopsBenchmarkSuite.floor_latencies(latencies)

    # --- assert ------------------------------------------
    assert floored[FlopType.ABS] == FlopsBenchmarkSuite.MIN_LATENCY_ADD_FRACTION * latencies[FlopType.ADD]
    assert all(v > 0 for v in floored.values())


def test_floor_latencies_survives_non_positive_add():
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ADD: -1.0, FlopType.ABS: -2.0})

    # --- act ---------------------------------------------
    floored = FlopsBenchmarkSuite.floor_latencies(latencies)

    # --- assert ------------------------------------------
    assert all(v > 0 for v in floored.values())


def test_floored_latencies_yield_finite_positive_weights():
    # --- arrange -----------------------------------------
    latencies = _latencies({FlopType.ABS: -0.5, FlopType.MINUS: 0.0})

    # --- act ---------------------------------------------
    weights = FlopWeights.from_abs_flop_costs(FlopsBenchmarkSuite.floor_latencies(latencies))

    # --- assert ------------------------------------------
    assert all(math.isfinite(w) and w > 0 for w in weights.weights.values())
