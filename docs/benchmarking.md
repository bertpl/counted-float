# Benchmarking

## Benchmarking your own hardware

If the package is installed with the optional `benchmarking` dependency, it provides
the ability to micro-benchmark floating point operations as follows:

The run below is a frozen example, captured on an Apple M3 Max; your own
numbers will differ.

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

Running FLOPS benchmarks using counted-float 1.7.0 ...
(Expected duration: ~183 seconds, plus jit compilation & calibration)

setup     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45/45   0:00:00
jit       ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45/45   0:00:01
calibrate ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10   0:00:06
warmup    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/3     0:00:02
measure   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 200/200 0:02:56

>>> results.flop_weights().show()

{
    FlopType.COPYSIGN   [copysign(x,y)] :   0.87831
    FlopType.MINUS      [-x]            :   0.90193
    FlopType.ABS        [abs(x)]        :   0.90363
    FlopType.SUB        [x-y]           :   0.99836
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.RND        [round]         :   1.23959
    FlopType.FMA        [x*y+z]         :   1.49503
    FlopType.MUL        [x*y]           :   1.49575
    FlopType.COMP       [x<=y]          :   1.66421
    FlopType.DIV        [x/y]           :   3.95925
    FlopType.SQRT       [sqrt(x)]       :   5.06561
    FlopType.FMOD       [fmod(x,y)]     :   6.21345
    FlopType.HYPOT      [hypot(x,y)]    :  15.19485
    FlopType.EXP2       [2^x]           :  16.34974
    FlopType.LOG10      [log10(x)]      :  17.00526
    FlopType.EXP        [e^x]           :  17.02853
    FlopType.LOG        [log(x)]        :  17.29792
    FlopType.LOG2       [log2(x)]       :  17.75923
    FlopType.ACOSH      [acosh(x)]      :  18.83182
    FlopType.COSH       [cosh(x)]       :  18.99199
    FlopType.EXP10      [10^x]          :  19.91784
    FlopType.SINH       [sinh(x)]       :  20.33317
    FlopType.EXPM1      [expm1(x)]      :  20.65683
    FlopType.CBRT       [cbrt(x)]       :  20.81894
    FlopType.LOG1P      [log1p(x)]      :  20.92136
    FlopType.ASINH      [asinh(x)]      :  22.20889
    FlopType.ACOS       [acos(x)]       :  24.85752
    FlopType.TANH       [tanh(x)]       :  26.35794
    FlopType.SIN        [sin(x)]        :  28.04244
    FlopType.ATAN       [atan(x)]       :  28.10357
    FlopType.ASIN       [asin(x)]       :  28.17009
    FlopType.COS        [cos(x)]        :  28.31717
    FlopType.ATAN2      [atan2(y,x)]    :  29.76497
    FlopType.TAN        [tan(x)]        :  31.46474
    FlopType.ATANH      [atanh(x)]      :  31.59515
    FlopType.POW        [x^y]           :  37.72695
    FlopType.F2I        [float->int]    :       nan
    FlopType.I2F        [int->float]    :       nan
}
```

All benchmark probes run round-robin interleaved: each measurement round runs
every probe for one short (~20 ms) time slice, in an order re-shuffled per
round. Any machine-wide disturbance (a background process waking up, thermal
throttling) then hits all probes approximately equally and cancels in the
pairwise differences the FLOP latencies are derived from; per-probe latency
is estimated from a low quantile (q10) of its recorded slices, which discards
residual burst-contaminated rounds. An optional `seed` argument makes the
input data and round order reproducible.

The fused multiply-add probes are the one exception to how the probes are
compiled: they alone enable LLVM's `contract` fast-math flag, because a
multiply-add is fused into a single FMA instruction only where the compiler is
permitted to, and without that permission the probes would time a separate
multiply and add and report the result as an FMA latency. Only `contract` is
granted — not the blanket fast-math switch, which would also permit
reassociation and no-NaN/no-Inf assumptions that have no place in a latency
measurement — and only on those probes, so every other measurement times the
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
`counted_float evaluate-overhead` (see the
[CLI reference](cli.md)) teaches us this — again a frozen example, captured on
an Apple M3 Max with counted-float 2.1.0:

```
------------------------------------------------------------------------------------------------------------------------
Evaluating counting overhead...

float                              : wwwwwwwwwwwwwww...................................   [  12.62 µs ±  0.9% ]  /  execution
CountedFloat                       : wwwwwwwwwwwwwww...................................   [ 271.80 µs ±  0.6% ]  /  execution
------------------------------------------------------------------------------------------------------------------------

Counting overhead:
  Bisection using float        :   12.62 µs / execution
  Bisection using CountedFloat :  271.80 µs / execution

CountedFloat is 21.5x slower than float
```
