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

The size of that impact depends almost entirely on the operation mix, so
`counted_float evaluate-overhead` (see the [CLI reference](cli.md)) measures it
in three layers: a per-flop-type table (each type timed on its generic counting
path, float vs `CountedFloat`, per operation), the geomean of those ratios as a
single summary figure, and a practical mixed workload — a bisection whose zero
function does lgamma work — showing where a realistic blend of cheap operator
work and expensive `math` calls lands between the endpoints. Again a frozen
example, captured on an Apple M3 Max with CPython 3.13 and counted-float 2.3.0
(per-run progress lines elided):

```
Counting overhead per flop type (CountedFloat vs float, generic counting path):
  FlopType.ABS            [abs(x)]          abs(x)                      :     10.54 ns ->    127.61 ns  =    12.1x
  FlopType.MINUS          [-x]              -x                          :      7.87 ns ->    126.53 ns  =    16.1x
  FlopType.COPYSIGN       [copysign(x,y)]   math.copysign(x, y)         :     17.66 ns ->    125.45 ns  =     7.1x
  FlopType.COMP           [x<=y]            x <= y                      :      8.44 ns ->    105.33 ns  =    12.5x
  FlopType.RND            [round]           round(x, 0)                 :    114.40 ns ->    252.02 ns  =     2.2x
  FlopType.F2I            [float->int]      int(x)                      :      8.96 ns ->     71.85 ns  =     8.0x
  FlopType.I2F            [int->float]      CountedFloat(i) vs float(i) :     12.87 ns ->    151.71 ns  =    11.8x
  FlopType.ADD            [x+y]             x + y                       :      9.64 ns ->    175.85 ns  =    18.2x
  FlopType.SUB            [x-y]             x - y                       :      9.55 ns ->    175.44 ns  =    18.4x
  FlopType.MUL            [x*y]             x * y                       :      9.65 ns ->    186.54 ns  =    19.3x
  FlopType.DIV            [x/y]             x / y                       :     11.80 ns ->    237.74 ns  =    20.1x
  FlopType.FMA            [x*y+z]           math.fma(x, y, z)           :     16.17 ns ->    134.29 ns  =     8.3x
  FlopType.SQRT           [sqrt(x)]         math.sqrt(x)                :     13.81 ns ->    116.83 ns  =     8.5x
  FlopType.CBRT           [cbrt(x)]         math.cbrt(x)                :     16.57 ns ->    122.60 ns  =     7.4x
  FlopType.EXP            [e^x]             math.exp(x)                 :     15.63 ns ->    119.52 ns  =     7.6x
  FlopType.EXP2           [2^x]             math.exp2(x)                :     15.85 ns ->    119.37 ns  =     7.5x
  FlopType.EXP10          [10^x]            10.0 ** x                   :     22.50 ns ->    257.88 ns  =    11.5x
  FlopType.LOG            [log(x)]          math.log(x)                 :     17.08 ns ->    135.80 ns  =     7.9x
  FlopType.LOG2           [log2(x)]         math.log2(x)                :     16.53 ns ->    119.96 ns  =     7.3x
  FlopType.LOG10          [log10(x)]        math.log10(x)               :     16.76 ns ->    120.20 ns  =     7.2x
  FlopType.POW            [x^y]             x ** y                      :     25.95 ns ->    288.31 ns  =    11.1x
  FlopType.SIN            [sin(x)]          math.sin(x)                 :     17.78 ns ->    124.60 ns  =     7.0x
  FlopType.COS            [cos(x)]          math.cos(x)                 :     18.26 ns ->    124.79 ns  =     6.8x
  FlopType.TAN            [tan(x)]          math.tan(x)                 :     19.67 ns ->    126.48 ns  =     6.4x
  FlopType.ASIN           [asin(x)]         math.asin(x)                :     18.72 ns ->    125.11 ns  =     6.7x
  FlopType.ACOS           [acos(x)]         math.acos(x)                :     18.27 ns ->    124.40 ns  =     6.8x
  FlopType.ATAN           [atan(x)]         math.atan(x)                :     18.06 ns ->    124.10 ns  =     6.9x
  FlopType.ATAN2          [atan2(y,x)]      math.atan2(x, y)            :     24.00 ns ->    132.81 ns  =     5.5x
  FlopType.HYPOT          [hypot(x,y)]      math.hypot(x, y)            :     26.75 ns ->    253.40 ns  =     9.5x
  FlopType.EXPM1          [expm1(x)]        math.expm1(x)               :     16.57 ns ->    121.37 ns  =     7.3x
  FlopType.LOG1P          [log1p(x)]        math.log1p(x)               :     16.99 ns ->    121.48 ns  =     7.1x
  FlopType.FMOD           [fmod(x,y)]       math.fmod(x, y)             :     18.48 ns ->    123.64 ns  =     6.7x
  FlopType.REMAINDER      [remainder(x,y)]  math.remainder(x, y)        :     20.58 ns ->    126.65 ns  =     6.2x
  FlopType.SINH           [sinh(x)]         math.sinh(x)                :     17.18 ns ->    121.72 ns  =     7.1x
  FlopType.COSH           [cosh(x)]         math.cosh(x)                :     17.14 ns ->    122.43 ns  =     7.1x
  FlopType.TANH           [tanh(x)]         math.tanh(x)                :     18.97 ns ->    125.03 ns  =     6.6x
  FlopType.ASINH          [asinh(x)]        math.asinh(x)               :     21.15 ns ->    129.68 ns  =     6.1x
  FlopType.ACOSH          [acosh(x)]        math.acosh(x)               :     19.72 ns ->    126.77 ns  =     6.4x
  FlopType.ATANH          [atanh(x)]        math.atanh(x)               :     20.24 ns ->    127.63 ns  =     6.3x
  FlopType.DIST           [dist(p,q)]       math.dist(p, q)             :     29.87 ns ->    383.19 ns  =    12.8x
  FlopType.SUMPROD        [sumprod(p,q)]    math.sumprod(p, q)          :     53.96 ns ->    539.57 ns  =    10.0x
  FlopType.GAMMA          [gamma(x)]        math.gamma(x)               :     32.31 ns ->    137.15 ns  =     4.2x
  FlopType.LGAMMA         [lgamma(x)]       math.lgamma(x)              :     27.87 ns ->    137.13 ns  =     4.9x
  FlopType.ERF            [erf(x)]          math.erf(x)                 :     22.56 ns ->    128.69 ns  =     5.7x
  FlopType.ERFC           [erfc(x)]         math.erfc(x)                :     20.94 ns ->    125.84 ns  =     6.0x

Not measured:
  FlopType.HYPOT_XARG     [hypot(+arg)]     cost increment per hypot() argument beyond two; not a standalone operation
  FlopType.DIST_XARG      [dist(+arg)]      cost increment per dist() dimension beyond two; not a standalone operation
  FlopType.SUMPROD_XELEM  [sumprod(+elem)]  cost increment per sumprod() element beyond two; not a standalone operation

Geomean overhead across measured flop types: 8.1x

Practical workload: bisection of lgamma(x) - 10.0 on [2.0, 100.0]
  float        :    5.57 µs / execution
  CountedFloat :   51.87 µs / execution

CountedFloat is 9.3x slower than float on this workload
```
