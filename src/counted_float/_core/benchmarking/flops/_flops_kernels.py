"""The numba kernels the flops benchmark measures, one per benchmark type.

Each kernel is a doubly-nested loop by design: the outer repeats to fill a timing slice, the inner
walks the input array in a dependent chain, so the measurement reflects operation latency rather
than the CPU's ability to overlap independent work.
"""

import math

import numpy as np

from counted_float._core.compatibility import numba


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
def f_add_halfsin_atanh(n_executions: int, n: int, in_f: np.ndarray, out_f: np.ndarray, out_i: np.ndarray) -> None:
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
