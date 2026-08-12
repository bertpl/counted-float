import math
import re

import numpy as np
import pytest

from counted_float._core.benchmarking.flops import FlopsBenchmarkSuite, FlopsMicroBenchmark
from counted_float._core.benchmarking.flops import flops_probes as probes
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
        array_size=16,
        t_slice_target_ms=0.1,
        n_rounds_measure=5,
        n_rounds_warmup=1,
        seed=42,
    )  # override defaults to keep test short

    # --- assert ------------------------------------------
    assert isinstance(result, FlopsBenchmarkResults)


def test_flops_benchmarking_suite_rejects_too_small_arrays():
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="array_size"):
        suite.get_flops_benchmarking_suite(size=FlopsBenchmarkSuite.MIN_ARRAY_SIZE - 1)


def test_suite_measures_the_arity_flop_types():
    """The arity probe pairs feed the base + per-extra-element flop types with sane, ordered latencies."""
    # --- arrange -----------------------------------------
    suite = FlopsBenchmarkSuite()

    # --- act ---------------------------------------------
    result = suite.run(array_size=1000, t_slice_target_ms=2.0, n_rounds_measure=15, n_rounds_warmup=2, seed=7)
    efl = result.estimated_flop_latencies

    # --- assert ------------------------------------------
    for flop_type in (FlopType.HYPOT_XARG, FlopType.DIST, FlopType.DIST_XARG, FlopType.SUMPROD, FlopType.SUMPROD_XELEM):
        assert math.isfinite(efl[flop_type]), flop_type
        assert efl[flop_type] > 0, flop_type
    # an extra coordinate is far cheaper than a whole 2-arg call (its squares overlap the sqrt path)
    assert efl[FlopType.HYPOT_XARG] < efl[FlopType.HYPOT]
    assert efl[FlopType.DIST_XARG] < efl[FlopType.DIST]
    # an extra element is at most the 2-element base (which carries the close-out on top)
    assert efl[FlopType.SUMPROD_XELEM] < efl[FlopType.SUMPROD]


def test_remainder_probe_matches_math_remainder():
    """The ctypes-bound libm call must compute exactly what math.remainder computes.

    numba has no math.remainder, so the probe calls libm through ctypes -- this pins that the
    bound symbol is the right function (IEEE remainder, not fmod).
    """
    # --- arrange -----------------------------------------
    n = 50
    in_f = np.exp(np.linspace(np.log(1e-16), np.log(1e16), n))
    out_f, out_i = np.zeros(n), np.zeros(n, dtype=int)

    # --- act ---------------------------------------------
    probes.f_add_remainder(1, n, in_f, out_f, out_i)

    # --- assert ------------------------------------------
    tmp = math.e
    for i in range(n):
        tmp = math.remainder(tmp + in_f[i], in_f[i])
        assert out_f[i] == tmp


def test_cbrt_probe_matches_math_cbrt():
    """The ctypes-bound libm call must compute exactly what math.cbrt computes.

    The probe calls libm through ctypes rather than through numba's np.cbrt, whose NaN/sign
    wrapper CPython's math.cbrt never executes -- this pins that the bound symbol is the right
    function, negative arguments included.
    """
    # --- arrange -----------------------------------------
    n = 50
    in_f = np.linspace(-1e16, 1e16, n)
    out_f, out_i = np.zeros(n), np.zeros(n, dtype=int)

    # --- act ---------------------------------------------
    probes.f_add_cbrt(1, n, in_f, out_f, out_i)

    # --- assert ------------------------------------------
    tmp = math.e
    for i in range(n):
        tmp = math.cbrt(tmp + in_f[i])
        assert out_f[i] == tmp


@pytest.mark.skipif(not hasattr(math, "sumprod"), reason="the reference value needs math.sumprod (Python 3.12+)")
@pytest.mark.parametrize("arity", [2, 8])
def test_sumprod_probes_match_math_sumprod(arity: int):
    """The ported TripleLength accumulation must compute exactly what math.sumprod computes.

    Bit-exact equality is what pins the port as faithful: any deviation -- a dropped error term,
    a reassociated sum, a non-fused multiply-add -- shows up as a differing last bit on inputs
    like these. The reference feeds plain floats (math.sumprod's compensated path is gated on
    exact floats, so numpy scalars would reroute it to the naive object path).
    """
    # --- arrange -----------------------------------------
    n = 50
    rng = np.random.default_rng(3)
    in_f = rng.uniform(-1.0, 1.0, n)
    out_f, out_i = np.zeros(n), np.zeros(n, dtype=int)
    probe = {2: probes.f_add_sumprod2, 8: probes.f_add_sumprod8}[arity]

    # --- act ---------------------------------------------
    probe(1, n, in_f, out_f, out_i)

    # --- assert ------------------------------------------
    tmp = math.e
    for i in range(n):
        p = [tmp + float(in_f[i])] + [float(in_f[i - k]) for k in range(2, 2 * arity, 2)]
        q = [float(in_f[i - k]) for k in range(1, 2 * arity, 2)]
        tmp = math.sumprod(p, q)
        assert out_f[i] == tmp


@pytest.mark.parametrize("probe", [probes.f_add_gammabase_gamma, probes.f_add_gammabase_lgamma])
def test_gamma_probes_never_overflow_even_on_a_wild_input_range(probe):
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
    probe(50, 2000, in_f, out_f, out_i)

    # --- assert ------------------------------------------
    assert np.all(np.isfinite(out_f))


# =================================================================================================
#  FMA probe fusion
# =================================================================================================
# fused multiply-add mnemonics, and their unfused counterparts, on aarch64 and x86-64
_FUSED = re.compile(r"\b(fmadd|fmsub|fnmadd|fnmsub|vfmadd\w*|vfmsub\w*)\b", re.IGNORECASE)
_UNFUSED_MUL_ADD = re.compile(r"\b(fmul|fadd|mulsd|addsd|vmulsd|vaddsd)\b", re.IGNORECASE)


def _probe_assembly(benchmark: FlopsMicroBenchmark) -> str:
    """Compile a benchmark's probe and return the assembly emitted for it."""
    # njit compiles lazily, so run the probe once to give it a signature to report on
    in_f = benchmark.array_init.new_array(benchmark.size)
    benchmark.f(1, benchmark.size, in_f, np.zeros(benchmark.size), np.zeros(benchmark.size, dtype=int))
    return "\n".join(benchmark.f.inspect_asm().values())


@pytest.mark.parametrize("benchmark_type", [FlopsBenchmarkType.FMA, FlopsBenchmarkType.FMA_FMA])
def test_fma_probes_compile_to_fused_multiply_adds(benchmark_type: FlopsBenchmarkType):
    """Each multiply-add in the FMA probes must collapse into one fused instruction, leaving none behind.

    This is what makes the FMA latency estimate falsifiable. A toolchain that stopped contracting would
    leave the pair measuring a separate multiply and add while still reporting the difference as an FMA
    latency, and nothing else in the suite would notice.

    Instruction counts are deliberately not asserted: LLVM's unroll factor differs per probe and across
    versions, so a count pins a heuristic rather than the property that matters.
    """
    # --- arrange -----------------------------------------
    benchmark = FlopsBenchmarkSuite.get_flops_benchmarking_suite(size=100)[benchmark_type]

    # --- act ---------------------------------------------
    asm = _probe_assembly(benchmark)

    # --- assert ------------------------------------------
    assert _FUSED.search(asm), "multiply-add did not fuse: this probe measures MUL + ADD, not FMA"
    assert not _UNFUSED_MUL_ADD.search(asm), "an unfused multiply or add survived in an FMA probe"


@pytest.mark.parametrize("benchmark_type", [FlopsBenchmarkType.ADD_SUMPROD2, FlopsBenchmarkType.ADD_SUMPROD8])
def test_sumprod_probes_emit_fused_error_terms(benchmark_type: FlopsBenchmarkType):
    """The sumprod probes' per-element error term must compile to a fused multiply-add.

    The term is emitted through the llvm.fma intrinsic rather than fastmath contraction (LLVM
    CSEs the error term's multiply with the product's and never contracts it), so this pins that
    the intrinsic really lowers to a fused instruction. Unfused multiplies and adds legitimately
    remain: the compensated sums are real adds by construction.
    """
    # --- arrange -----------------------------------------
    benchmark = FlopsBenchmarkSuite.get_flops_benchmarking_suite(size=100)[benchmark_type]

    # --- act ---------------------------------------------
    asm = _probe_assembly(benchmark)

    # --- assert ------------------------------------------
    assert _FUSED.search(asm), "the error term did not fuse: the probe is not the TripleLength algorithm"


@pytest.mark.parametrize(
    "benchmark_type",
    [FlopsBenchmarkType.ADD, FlopsBenchmarkType.ADD_ADD, FlopsBenchmarkType.MUL, FlopsBenchmarkType.MUL_MUL],
)
def test_contraction_is_scoped_to_the_fma_probes(benchmark_type: FlopsBenchmarkType):
    """No other probe may fuse: the ADD and MUL pairs have to measure the operation they are named for."""
    # --- arrange -----------------------------------------
    benchmark = FlopsBenchmarkSuite.get_flops_benchmarking_suite(size=100)[benchmark_type]

    # --- act ---------------------------------------------
    asm = _probe_assembly(benchmark)

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
