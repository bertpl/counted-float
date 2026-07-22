"""The numba kernels the flops benchmark measures, one per benchmark type.

Each kernel is a doubly-nested loop by design: the outer repeats to fill a timing slice, the inner
walks the input array in a dependent chain, so the measurement reflects operation latency rather
than the CPU's ability to overlap independent work.
"""

import math

import numpy as np

from counted_float._core.compatibility import numba

from ._libm_bindings import libm_cbrt, libm_remainder

# the two probes that measure through a ctypes binding rather than a numba-compiled call --
# see _libm_bindings for the mechanism and the admission criterion
c_cbrt = libm_cbrt()
c_remainder = libm_remainder()


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
def f_add_copysign(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = math.copysign(tmp + in_f[i], in_f[i])
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
    # libm cbrt via ctypes (see _libm_bindings): numba's np.cbrt would wrap the call in NaN/sign
    # handling that CPython's math.cbrt never executes, so the bare call is what gets priced
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = c_cbrt(tmp + in_f[i])
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
def f_add_log10_exp10(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
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


# The arity kernels below hand-roll the overflow-safe scaling a faithful port of math.hypot /
# math.dist emits -- numba cannot compile the n-ary stdlib forms, and a spike confirmed this scaled
# form reproduces libm's 2-arg hypot cost to within ~10% (a naive sum-of-squares comes in at ~half,
# so it would under-price every coordinate). Each coordinate is divided by the largest magnitude
# before squaring, so no intermediate overflows -- the extra abs/compare/scale per coordinate is
# the real cost these measure. The dependency runs through the first coordinate; the rest read
# distinct array elements at small negative offsets (valid for any n >= 8, far below the suite's
# ~1000). Differencing the arity-2 and arity-8 forms yields the per-extra-coordinate slope.
@numba.njit(parallel=False)
def f_add_hypot_scaled2(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            c0 = tmp + in_f[i]
            c1 = in_f[i - 1]
            m = max(abs(c0), abs(c1))
            inv = 1.0 / m
            t0 = c0 * inv
            t1 = c1 * inv
            tmp = m * math.sqrt(t0 * t0 + t1 * t1)
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_hypot_scaled8(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            c0 = tmp + in_f[i]
            m = abs(c0)
            m = max(m, abs(in_f[i - 1]))
            m = max(m, abs(in_f[i - 2]))
            m = max(m, abs(in_f[i - 3]))
            m = max(m, abs(in_f[i - 4]))
            m = max(m, abs(in_f[i - 5]))
            m = max(m, abs(in_f[i - 6]))
            m = max(m, abs(in_f[i - 7]))
            inv = 1.0 / m
            t = c0 * inv
            s = t * t
            t = in_f[i - 1] * inv
            s += t * t
            t = in_f[i - 2] * inv
            s += t * t
            t = in_f[i - 3] * inv
            s += t * t
            t = in_f[i - 4] * inv
            s += t * t
            t = in_f[i - 5] * inv
            s += t * t
            t = in_f[i - 6] * inv
            s += t * t
            t = in_f[i - 7] * inv
            s += t * t
            tmp = m * math.sqrt(s)
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_dist2(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            c0 = (tmp + in_f[i]) - in_f[i - 1]
            c1 = in_f[i - 1] - in_f[i - 2]
            m = max(abs(c0), abs(c1))
            inv = 1.0 / m
            t0 = c0 * inv
            t1 = c1 * inv
            tmp = m * math.sqrt(t0 * t0 + t1 * t1)
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_dist8(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            c0 = (tmp + in_f[i]) - in_f[i - 1]
            c1 = in_f[i - 1] - in_f[i - 2]
            c2 = in_f[i - 2] - in_f[i - 3]
            c3 = in_f[i - 3] - in_f[i - 4]
            c4 = in_f[i - 4] - in_f[i - 5]
            c5 = in_f[i - 5] - in_f[i - 6]
            c6 = in_f[i - 6] - in_f[i - 7]
            c7 = in_f[i - 7] - in_f[i - 8]
            m = abs(c0)
            m = max(m, abs(c1))
            m = max(m, abs(c2))
            m = max(m, abs(c3))
            m = max(m, abs(c4))
            m = max(m, abs(c5))
            m = max(m, abs(c6))
            m = max(m, abs(c7))
            inv = 1.0 / m
            t = c0 * inv
            s = t * t
            t = c1 * inv
            s += t * t
            t = c2 * inv
            s += t * t
            t = c3 * inv
            s += t * t
            t = c4 * inv
            s += t * t
            t = c5 * inv
            s += t * t
            t = c6 * inv
            s += t * t
            t = c7 * inv
            s += t * t
            tmp = m * math.sqrt(s)
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_log1p(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = math.log1p(tmp + in_f[i])
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_log1p_expm1(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
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
def f_add_remainder(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    # libm remainder via ctypes (see module header); the positive divisor range avoids the
    # remainder(x, 0) domain error, mirroring the fmod kernel
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = c_remainder(tmp + in_f[i], in_f[i])
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
    # the positive range keeps the argument >= 1 (acosh's domain); see the suite registration for
    # why its magnitude is moderate
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
def f_add_halfsin_atanh(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    # 0.5*sin bounds the argument well inside (-1, 1); subtract add_halfsin to isolate the atanh cost
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = math.atanh(0.5 * math.sin(tmp + in_f[i]))
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_gammabase(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    # shared baseline for gamma/lgamma: 1.5 + 0.5*sin pins the fed-back argument to [1, 2], straddling
    # gamma's minimum (~1.4618). gamma/lgamma have no cheap inverse to bound the chain (unlike
    # sinh/atanh), and their outputs grow without bound, so a naive f(tmp + in_f[i]) chain diverges into
    # OverflowError; the sin bound keeps the chain finite. Subtract this to isolate the gamma/lgamma cost.
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = 1.5 + 0.5 * math.sin(tmp + in_f[i])
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_gammabase_gamma(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    # f_add_gammabase plus the gamma call: 1.5 + 0.5*sin bounds the argument to [1, 2], where gamma's
    # output stays in [~0.886, 1] so the chain never overflows; subtract f_add_gammabase to isolate gamma
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = math.gamma(1.5 + 0.5 * math.sin(tmp + in_f[i]))
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_gammabase_lgamma(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    # f_add_gammabase plus the lgamma call (lgamma also grows without bound); subtract f_add_gammabase
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = math.lgamma(1.5 + 0.5 * math.sin(tmp + in_f[i]))
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_erf(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    # erf's output is bounded to (-1, 1), so the naive chain never diverges; the small positive input
    # range keeps the argument clear of the |x|<~0.5 and |x|>~6 cheap fast-paths (see suite registration)
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = math.erf(tmp + in_f[i])
            out_f[i] = tmp


@numba.njit(parallel=False)
def f_add_erfc(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    # erfc's output is bounded to (0, 2); the small positive input range keeps the argument below the
    # x>~27 underflow-to-zero fast-path (see suite registration)
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = math.erfc(tmp + in_f[i])
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


# the two FMA kernels are the only ones compiled with contraction enabled: LLVM fuses a
# multiply-add into a single FMA instruction only when granted permission, so without the
# flag `tmp * in_f[i] + in_f[i]` emits a separate multiply and add and the pair below would
# measure MUL + ADD while reporting FMA.  Only the `contract` flag is granted -- the blanket
# fastmath=True would also permit reassociation and no-NaN/no-Inf assumptions, which have no
# place in a latency measurement.  Contraction stays scoped to these two kernels: no other
# kernel needs it, and the suite's tests pin that the fusion lands here and nowhere else.
@numba.njit(parallel=False, fastmath={"contract"})
def f_fma(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = tmp * in_f[i] + in_f[i]
            out_f[i] = tmp


@numba.njit(parallel=False, fastmath={"contract"})
def f_fma_fma(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
    for _ in range(n_executions):
        tmp = math.e
        for i in range(n):
            tmp = tmp * in_f[i] + in_f[i]
            tmp = tmp * in_f[i] + in_f[i]
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
