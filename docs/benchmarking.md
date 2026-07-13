# Benchmarking

## Benchmarking your own hardware

If the package is installed with the optional `numba` dependency, it provides
the ability to micro-benchmark floating point operations as follows:

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

Running FLOPS benchmarks using counted-float 1.4.2 ...
(Expected duration: ~171 seconds, plus jit compilation & calibration)

setup calibrate warmup measure .................... done

>>> results.flop_weights().show()

{
    FlopType.ABS        [abs(x)]        :   0.90066
    FlopType.MINUS      [-x]            :   0.90185
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   1.00006
    FlopType.RND        [round]         :   1.23318
    FlopType.MUL        [x*y]           :   1.49293
    FlopType.COMP       [x<=y]          :   1.65702
    FlopType.DIV        [x/y]           :   3.96976
    FlopType.SQRT       [sqrt(x)]       :   5.08313
    FlopType.FMOD       [fmod(x,y)]     :   6.19209
    FlopType.HYPOT      [hypot(x,y)]    :  15.12720
    FlopType.EXP2       [2^x]           :  16.32379
    FlopType.EXP        [e^x]           :  16.97535
    FlopType.LOG10      [log10(x)]      :  16.98483
    FlopType.LOG        [log(x)]        :  17.25491
    FlopType.LOG2       [log2(x)]       :  17.68443
    FlopType.ACOSH      [acosh(x)]      :  18.82279
    FlopType.COSH       [cosh(x)]       :  18.95751
    FlopType.EXP10      [10^x]          :  19.91439
    FlopType.SINH       [sinh(x)]       :  20.30701
    FlopType.EXPM1      [expm1(x)]      :  20.57782
    FlopType.CBRT       [cbrt(x)]       :  20.74467
    FlopType.LOG1P      [log1p(x)]      :  20.92068
    FlopType.ASINH      [asinh(x)]      :  22.12902
    FlopType.ACOS       [acos(x)]       :  24.64399
    FlopType.TANH       [tanh(x)]       :  26.17544
    FlopType.ASIN       [asin(x)]       :  27.77200
    FlopType.ATAN       [atan(x)]       :  27.95380
    FlopType.SIN        [sin(x)]        :  28.04906
    FlopType.COS        [cos(x)]        :  28.43823
    FlopType.ATAN2      [atan2(y,x)]    :  29.67176
    FlopType.ATANH      [atanh(x)]      :  31.47494
    FlopType.TAN        [tan(x)]        :  31.53547
    FlopType.POW        [x^y]           :  37.44672
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

float                              : wwwwwwwwwwwwwww...................................   [  12.34 µs ±  1.2% | 50.1K cpu cycles ±  1.2% ]  /  execution
CountedFloat                       : wwwwwwwwwwwwwww...................................   [ 459.95 µs ±  0.2% | 1.87M cpu cycles ±  0.2% ]  /  execution
------------------------------------------------------------------------------------------------------------------------

CountedFloat Benchmark Results:
  Bisection using float        :   12.34 µs / execution
  Bisection using CountedFloat :  459.95 µs / execution

CountedFloat is 37.3x slower than float
```
