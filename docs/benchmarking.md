# Benchmarking

## Benchmarking your own hardware

If the package is installed with the optional `numba` dependency, it provides
the ability to micro-benchmark floating point operations as follows:

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

Running FLOPS benchmarks using counted-float 0.9.5 ...
(Expected duration: ~87.8 seconds)

baseline                           : wwwwwwwwwwwwwww.........................   [  74.43 ns ±  2.6% |   302 cpu cycles ±  2.6% ]  /  1000 iterations
add                                : wwwwwwwwwwwwwww.........................   [ 662.35 ns ±  0.2% | 2.69K cpu cycles ±  0.2% ]  /  1000 iterations
add_minus                          : wwwwwwwwwwwwwww.........................   [   1.23 µs ±  0.2% | 4.98K cpu cycles ±  0.2% ]  /  1000 iterations
add_abs                            : wwwwwwwwwwwwwww.........................   [   1.23 µs ±  0.4% | 4.99K cpu cycles ±  0.4% ]  /  1000 iterations
add_add                            : wwwwwwwwwwwwwww.........................   [   1.29 µs ±  0.2% | 5.23K cpu cycles ±  0.2% ]  /  1000 iterations
add_sub                            : wwwwwwwwwwwwwww.........................   [   1.29 µs ±  0.2% | 5.23K cpu cycles ±  0.2% ]  /  1000 iterations
add_round                          : wwwwwwwwwwwwwww.........................   [   1.44 µs ±  0.1% | 5.84K cpu cycles ±  0.1% ]  /  1000 iterations
add_sqrt                           : wwwwwwwwwwwwwww.........................   [   3.96 µs ±  0.2% | 16.1K cpu cycles ±  0.2% ]  /  1000 iterations
add_cbrt                           : wwwwwwwwwwwwwww.........................   [  25.42 µs ±  0.2% |  103K cpu cycles ±  0.2% ]  /  1000 iterations
add_log                            : wwwwwwwwwwwwwww.........................   [  11.69 µs ±  0.3% | 47.4K cpu cycles ±  0.3% ]  /  1000 iterations
add_log_exp                        : wwwwwwwwwwwwwww.........................   [  22.57 µs ±  0.1% | 91.5K cpu cycles ±  0.1% ]  /  1000 iterations
add_log2                           : wwwwwwwwwwwwwww.........................   [  12.00 µs ±  0.2% | 48.7K cpu cycles ±  0.2% ]  /  1000 iterations
add_log2_exp2                      : wwwwwwwwwwwwwww.........................   [  22.48 µs ±  0.2% | 91.2K cpu cycles ±  0.2% ]  /  1000 iterations
add_log10                          : wwwwwwwwwwwwwww.........................   [  11.50 µs ±  0.2% | 46.6K cpu cycles ±  0.2% ]  /  1000 iterations
add_log10_exp10                    : wwwwwwwwwwwwwww.........................   [  24.68 µs ±  0.2% |  100K cpu cycles ±  0.2% ]  /  1000 iterations
add_sin                            : wwwwwwwwwwwwwww.........................   [  18.64 µs ±  0.3% | 75.6K cpu cycles ±  0.3% ]  /  1000 iterations
add_cos                            : wwwwwwwwwwwwwww.........................   [  18.92 µs ±  0.3% | 76.7K cpu cycles ±  0.3% ]  /  1000 iterations
add_tan                            : wwwwwwwwwwwwwww.........................   [  20.91 µs ±  0.2% | 84.8K cpu cycles ±  0.2% ]  /  1000 iterations
pow                                : wwwwwwwwwwwwwww.........................   [  24.12 µs ±  0.3% | 97.8K cpu cycles ±  0.3% ]  /  1000 iterations
pow_pow                            : wwwwwwwwwwwwwww.........................   [  48.15 µs ±  0.2% |  195K cpu cycles ±  0.2% ]  /  1000 iterations
sub                                : wwwwwwwwwwwwwww.........................   [ 661.55 ns ±  0.2% | 2.68K cpu cycles ±  0.2% ]  /  1000 iterations
sub_sub                            : wwwwwwwwwwwwwww.........................   [   1.29 µs ±  0.2% | 5.24K cpu cycles ±  0.2% ]  /  1000 iterations
mul                                : wwwwwwwwwwwwwww.........................   [ 961.78 ns ±  0.2% | 3.90K cpu cycles ±  0.2% ]  /  1000 iterations
mul_mul                            : wwwwwwwwwwwwwww.........................   [   1.92 µs ±  0.2% | 7.78K cpu cycles ±  0.2% ]  /  1000 iterations
div                                : wwwwwwwwwwwwwww.........................   [   2.45 µs ±  0.2% | 9.92K cpu cycles ±  0.2% ]  /  1000 iterations
div_div                            : wwwwwwwwwwwwwww.........................   [   5.00 µs ±  0.2% | 20.3K cpu cycles ±  0.2% ]  /  1000 iterations
lte_addsub                         : wwwwwwwwwwwwwww.........................   [   1.71 µs ±  0.2% | 6.94K cpu cycles ±  0.2% ]  /  1000 iterations

>>> results.flop_weights().show()

{
    FlopType.ABS        [abs(x)]        :   0.89904
    FlopType.MINUS      [-x]            :   0.90935
    FlopType.SUB        [x-y]           :   0.99676
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.RND        [round]         :   1.24397
    FlopType.MUL        [x*y]           :   1.55516
    FlopType.COMP       [x<=y]          :   1.69018
    FlopType.DIV        [x/y]           :   4.12333
    FlopType.SQRT       [sqrt(x)]       :   5.42419
    FlopType.EXP2       [2^x]           :  16.95266
    FlopType.LOG10      [log10(x)]      :  17.60079
    FlopType.EXP        [e^x]           :  17.76250
    FlopType.LOG        [log(x)]        :  17.86149
    FlopType.LOG2       [log2(x)]       :  18.42380
    FlopType.EXP10      [10^x]          :  21.50729
    FlopType.SIN        [sin(x)]        :  29.31571
    FlopType.COS        [cos(x)]        :  29.56218
    FlopType.TAN        [tan(x)]        :  32.88570
    FlopType.POW        [x^y]           :  39.35018
    FlopType.CBRT       [cbrt(x)]       :  40.16857
    FlopType.F2I        [float->int]    :       nan
    FlopType.I2F        [int->float]    :       nan
}
```

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
