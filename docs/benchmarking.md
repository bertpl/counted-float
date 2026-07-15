# Benchmarking

## Benchmarking your own hardware

If the package is installed with the optional `numba` dependency, it provides
the ability to micro-benchmark floating point operations as follows:

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

Running FLOPS benchmarks using counted-float 1.6.0 ...
(Expected duration: ~179 seconds, plus jit compilation & calibration)

setup     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44/44   0:00:00
jit       ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44/44   0:00:09
calibrate ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10   0:00:04
warmup    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/3     0:00:03
measure   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 200/200 0:02:56

>>> results.flop_weights().show()

{
    FlopType.ABS        [abs(x)]        :   0.90086
    FlopType.MINUS      [-x]            :   0.90128
    FlopType.SUB        [x-y]           :   0.99924
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.RND        [round]         :   1.23358
    FlopType.FMA        [x*y+z]         :   1.49364
    FlopType.MUL        [x*y]           :   1.49670
    FlopType.COMP       [x<=y]          :   1.65971
    FlopType.DIV        [x/y]           :   3.96720
    FlopType.SQRT       [sqrt(x)]       :   5.08079
    FlopType.FMOD       [fmod(x,y)]     :   6.24736
    FlopType.HYPOT      [hypot(x,y)]    :  15.14849
    FlopType.EXP2       [2^x]           :  16.33827
    FlopType.EXP        [e^x]           :  16.93635
    FlopType.LOG10      [log10(x)]      :  17.01702
    FlopType.LOG        [log(x)]        :  17.34751
    FlopType.LOG2       [log2(x)]       :  17.73992
    FlopType.COSH       [cosh(x)]       :  18.84562
    FlopType.ACOSH      [acosh(x)]      :  19.00542
    FlopType.SINH       [sinh(x)]       :  20.24303
    FlopType.EXP10      [10^x]          :  20.32107
    FlopType.EXPM1      [expm1(x)]      :  20.54583
    FlopType.CBRT       [cbrt(x)]       :  20.77356
    FlopType.LOG1P      [log1p(x)]      :  20.99742
    FlopType.ASINH      [asinh(x)]      :  22.27093
    FlopType.ACOS       [acos(x)]       :  24.68559
    FlopType.TANH       [tanh(x)]       :  26.20514
    FlopType.ASIN       [asin(x)]       :  27.88059
    FlopType.SIN        [sin(x)]        :  28.08448
    FlopType.ATAN       [atan(x)]       :  28.12979
    FlopType.COS        [cos(x)]        :  28.49190
    FlopType.ATAN2      [atan2(y,x)]    :  29.74369
    FlopType.TAN        [tan(x)]        :  31.64899
    FlopType.ATANH      [atanh(x)]      :  31.65176
    FlopType.POW        [x^y]           :  37.55957
    FlopType.F2I        [float->int]    :       nan
    FlopType.I2F        [int->float]    :       nan
}
```

All benchmark kernels run round-robin interleaved: each measurement round runs
every kernel for one short (~20 ms) time slice, in an order re-shuffled per
round. Any machine-wide disturbance (a background process waking up, thermal
throttling) then hits all kernels approximately equally and cancels in the
pairwise differences the FLOP latencies are derived from; per-kernel latency
is estimated from a low quantile (q10) of its recorded slices, which discards
residual burst-contaminated rounds. An optional `seed` argument makes the
input data and round order reproducible.

The fused multiply-add kernels are the one exception to how the kernels are
compiled: they alone enable LLVM's `contract` fast-math flag, because a
multiply-add is fused into a single FMA instruction only where the compiler is
permitted to, and without that permission the kernels would time a separate
multiply and add and report the result as an FMA latency. Only `contract` is
granted — not the blanket fast-math switch, which would also permit
reassociation and no-NaN/no-Inf assumptions that have no place in a latency
measurement — and only on those kernels, so every other measurement times the
operation it is named for. The test suite pins both halves of that by inspecting
the emitted assembly.

The resulting weights can then be configured as the active flop weights — see
[Configuring FLOP weights](flop_weights.md#configuring-flop-weights).

## Performance impact

Obviously, using `CountedFloat` instead of regular `float` will have a
performance impact due to the overhead of counting operations. It is not
advised to use `CountedFloat` for production code, but just for research code
for which you want to estimate the floating-point operation count.

Micro-benchmarking of a bisection algorithm using
`counted_float benchmark-counted-float` (see the
[CLI reference](cli.md)) teaches us this:

```
------------------------------------------------------------------------------------------------------------------------
Running CountedFloat benchmark...

float                              : wwwwwwwwwwwwwww...................................   [  12.54 µs ±  3.7% | 50.8K cpu cycles ±  3.7% ]  /  execution
CountedFloat                       : wwwwwwwwwwwwwww...................................   [ 283.91 µs ±  0.3% | 1.15M cpu cycles ±  0.3% ]  /  execution
------------------------------------------------------------------------------------------------------------------------

CountedFloat Benchmark Results:
  Bisection using float        :   12.54 µs / execution
  Bisection using CountedFloat :  283.91 µs / execution

CountedFloat is 22.6x slower than float
```
