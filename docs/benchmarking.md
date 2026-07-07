# Benchmarking

## Benchmarking your own hardware

If the package is installed with the optional `numba` dependency, it provides
the ability to micro-benchmark floating point operations as follows:

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

Running FLOPS benchmarks using counted-float 1.2.1 ...
(Expected duration: ~87.8 seconds)

baseline                           : wwwwwwwwwwwwwww.........................   [   0.00 ns ±  3.6% |  0.00 cpu cycles ±  3.6% ]  /  1000 iterations
add                                : wwwwwwwwwwwwwww.........................   [ 641.59 ns ±  0.1% | 2.60K cpu cycles ±  0.1% ]  /  1000 iterations
add_minus                          : wwwwwwwwwwwwwww.........................   [   1.21 µs ±  0.1% | 4.91K cpu cycles ±  0.1% ]  /  1000 iterations
add_abs                            : wwwwwwwwwwwwwww.........................   [   1.21 µs ±  0.1% | 4.92K cpu cycles ±  0.1% ]  /  1000 iterations
add_add                            : wwwwwwwwwwwwwww.........................   [   1.27 µs ±  0.1% | 5.17K cpu cycles ±  0.1% ]  /  1000 iterations
add_sub                            : wwwwwwwwwwwwwww.........................   [   1.27 µs ±  0.1% | 5.17K cpu cycles ±  0.1% ]  /  1000 iterations
add_round                          : wwwwwwwwwwwwwww.........................   [   1.42 µs ±  0.1% | 5.77K cpu cycles ±  0.1% ]  /  1000 iterations
add_sqrt                           : wwwwwwwwwwwwwww.........................   [   3.86 µs ±  0.1% | 15.7K cpu cycles ±  0.1% ]  /  1000 iterations
add_cbrt                           : wwwwwwwwwwwwwww.........................   [  13.77 µs ±  0.1% | 55.9K cpu cycles ±  0.1% ]  /  1000 iterations
add_log                            : wwwwwwwwwwwwwww.........................   [  11.57 µs ±  0.1% | 46.9K cpu cycles ±  0.1% ]  /  1000 iterations
add_log_exp                        : wwwwwwwwwwwwwww.........................   [  22.43 µs ±  0.9% | 91.0K cpu cycles ±  0.9% ]  /  1000 iterations
add_log2                           : wwwwwwwwwwwwwww.........................   [  11.98 µs ±  1.9% | 48.6K cpu cycles ±  1.9% ]  /  1000 iterations
add_log2_exp2                      : wwwwwwwwwwwwwww.........................   [  23.62 µs ±  2.3% | 95.8K cpu cycles ±  2.3% ]  /  1000 iterations
add_log10                          : wwwwwwwwwwwwwww.........................   [  11.58 µs ±  1.1% | 47.0K cpu cycles ±  1.1% ]  /  1000 iterations
add_log10_exp10                    : wwwwwwwwwwwwwww.........................   [  24.12 µs ±  1.0% | 97.8K cpu cycles ±  1.0% ]  /  1000 iterations
add_sin                            : wwwwwwwwwwwwwww.........................   [  18.13 µs ±  0.2% | 73.5K cpu cycles ±  0.2% ]  /  1000 iterations
add_cos                            : wwwwwwwwwwwwwww.........................   [  18.35 µs ±  0.3% | 74.4K cpu cycles ±  0.3% ]  /  1000 iterations
add_tan                            : wwwwwwwwwwwwwww.........................   [  20.68 µs ±  0.7% | 83.9K cpu cycles ±  0.7% ]  /  1000 iterations
pow                                : wwwwwwwwwwwwwww.........................   [  23.83 µs ±  0.2% | 96.7K cpu cycles ±  0.2% ]  /  1000 iterations
pow_pow                            : wwwwwwwwwwwwwww.........................   [  48.59 µs ±  1.2% |  197K cpu cycles ±  1.2% ]  /  1000 iterations
sub                                : wwwwwwwwwwwwwww.........................   [ 646.33 ns ±  0.2% | 2.62K cpu cycles ±  0.2% ]  /  1000 iterations
sub_sub                            : wwwwwwwwwwwwwww.........................   [   1.28 µs ±  0.1% | 5.20K cpu cycles ±  0.1% ]  /  1000 iterations
mul                                : wwwwwwwwwwwwwww.........................   [ 956.45 ns ±  0.1% | 3.88K cpu cycles ±  0.1% ]  /  1000 iterations
mul_mul                            : wwwwwwwwwwwwwww.........................   [   1.91 µs ±  0.4% | 7.77K cpu cycles ±  0.4% ]  /  1000 iterations
div                                : wwwwwwwwwwwwwww.........................   [   2.44 µs ±  0.2% | 9.88K cpu cycles ±  0.2% ]  /  1000 iterations
div_div                            : wwwwwwwwwwwwwww.........................   [   4.96 µs ±  0.1% | 20.1K cpu cycles ±  0.1% ]  /  1000 iterations
lte_addsub                         : wwwwwwwwwwwwwww.........................   [   1.70 µs ±  0.1% | 6.91K cpu cycles ±  0.1% ]  /  1000 iterations


>>> results.flop_weights().show()

{
    FlopType.MINUS      [-x]            :   0.90134
    FlopType.ABS        [abs(x)]        :   0.90213
    FlopType.SUB        [x-y]           :   0.99990
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.RND        [round]         :   1.23559
    FlopType.MUL        [x*y]           :   1.51489
    FlopType.COMP       [x<=y]          :   1.67456
    FlopType.DIV        [x/y]           :   3.99607
    FlopType.SQRT       [sqrt(x)]       :   5.08751
    FlopType.EXP        [e^x]           :  17.17063
    FlopType.LOG        [log(x)]        :  17.28115
    FlopType.LOG10      [log10(x)]      :  17.29637
    FlopType.LOG2       [log2(x)]       :  17.92821
    FlopType.EXP2       [2^x]           :  18.40429
    FlopType.EXP10      [10^x]          :  19.82471
    FlopType.CBRT       [cbrt(x)]       :  20.75967
    FlopType.SIN        [sin(x)]        :  27.64850
    FlopType.COS        [cos(x)]        :  28.00054
    FlopType.TAN        [tan(x)]        :  31.67590
    FlopType.POW        [x^y]           :  39.14209
    FlopType.F2I        [float->int]    :       nan
    FlopType.I2F        [int->float]    :       nan
}
```

Note: the `baseline` benchmark may show ~0 ns on recent numba versions, whose
compiler can eliminate the baseline kernel's repetition loop entirely. This is
harmless: baseline timings are informational only — all estimated FLOP
latencies are differences between pairs of the other benchmarks.

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
