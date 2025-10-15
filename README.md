<!--START_SECTION:images-->
![shields.io-python-versions](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![genbadge-test-count](https://bertpl.github.io/counted-float/version_artifacts/v1.0.2/badge-test-count.svg)
![genbadge-test-coverage](https://bertpl.github.io/counted-float/version_artifacts/v1.0.2/badge-coverage.svg)
![counted_float logo](https://bertpl.github.io/counted-float/version_artifacts/v1.0.2/splash.webp)
<!--END_SECTION:images-->

# counted-float

This Python package provides functionality for...
- **counting floating point operations** (FLOPs) of numerical algorithms implemented in plain Python, optionally weighted by their relative cost of execution
- **running benchmarks** to estimate the relative cost of executing various floating-point operations (requires `numba` optional dependency for achieving accurate results)

The target application area is evaluation of research prototypes of numerical algorithms where (weighted) flop counting can be 
useful for estimating total computational cost, in cases where benchmarking a compiled version (C, Rust, ...) is not 
feasible or desirable.

Flop weights are computed using a highly curated dataset spanning a wide range of modern CPUs:
- 19 benchmarks, 16 spec sheets, 12 third party measurements (Agner Fog, uops.info)
- covering x86 (Intel, AMD) and ARM (Apple, AWS, Azure) architectures

# 1. Installation

Use you favorite package manager such as `uv` or `pip`:

```
pip install counted-float           # install without numba optional dependency
pip install counted-float[numba]    # install with numba optional dependency
```
Numba is optional due to its relatively large size (40-50MB, including llvmlite), but without it, benchmarks will
not be reliable (but will still run, but not in jit-compiled form).

NOTE: the `cli` optional dependency is only useful when installing the code as a tool using e.g. `uv` or `pipx` (see below)

# 2. Counting Flops

## 2.1. CountedFloat class

In order to instrument all floating point operations with counting functionality,
the `CountedFloat` class was implemented, which is a drop-in replacement for the built-in `float` type.
The `CountedFloat` class is a subclass of `float` and is "contagious", meaning that it will automatically
ensure results of math operations where at least one operand is a `CountedFloat` will also be a `CountedFloat`.
This way we ensure flop counting is a 'closed system'.

On top of this, we monkey-patch the `math` module to ensure that all math operations
that require counting (`sqrt`, `log2`, `pow`, ...) are also instrumented.

**Example 1**:

```python
from counted_float import CountedFloat

cf = CountedFloat(1.3)
f = 2.8

result = cf + f  # result = CountedFloat(4.1)

is_float_1 = isinstance(cf, float)  # True
is_float_2 = isinstance(result, float)  # True
```

**Example 2**:

```python
import math
from counted_float import CountedFloat

cf1 = CountedFloat(0.81)

s = math.sqrt(cf1)  # s = CountedFloat(0.9)
is_float = isinstance(s, float)  # True
```

## 2.2. FLOP counting context managers

Once we use the `CountedFloat` class, we can use the available context managers to count the number of
flops performed by `CountedFloat` objects.

**Example 1**:  _basic usage_
```python
from counted_float import CountedFloat, FlopCountingContext

cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 * cf2
    _ = cf1 + cf2

counts = ctx.flop_counts()   # {FlopType.MUL: 1, FlopType.ADD: 1}
counts.total_count()         # 2
```

**Example 2**:  _pause counting 1_

```python
from counted_float import CountedFloat, FlopCountingContext

cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 * cf2
    ctx.pause()
    _ = cf1 + cf2   # will be executed but not counted
    ctx.resume()
    _ = cf1 - cf2

counts = ctx.flop_counts()   # {FlopType.MUL: 1, FlopType.SUB: 1}
counts.total_count()         # 2
```

**Example 3**:  _pause counting 2_

```python
from counted_float import CountedFloat, FlopCountingContext, PauseFlopCounting

cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 * cf2
    with PauseFlopCounting():
        _ = cf1 + cf2   # will be executed but not counted
    _ = cf1 - cf2

counts = ctx.flop_counts()   # {FlopType.MUL: 1, FlopType.SUB: 1}
counts.total_count()         # 2
```

## 2.3. Weighted FLOP counting

The `counted_float` package contains a set of default, built-in FLOP weights, based on both empirical measurements
and theoretical estimates of the relative cost of different floating point operations. 

See [fpu_data_sources.md](https://github.com/bertpl/counted-float/tree/develop/docs/analysis_methodology.md) for
rationale behind choice of data sources and methodology.

```
>>> from counted_float.config import get_active_flop_weights
>>> get_active_flop_weights().show()

{
    FlopType.MINUS      [-x]            :   0.45000
    FlopType.ABS        [abs(x)]        :   0.70000
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.COMP       [x<=y]          :   1.00000
    FlopType.SUB        [x-y]           :   1.00000
    FlopType.MUL        [x*y]           :   1.40000
    FlopType.RND        [round]         :   1.80000
    FlopType.F2I        [float->int]    :   2.00000
    FlopType.I2F        [int->float]    :   2.00000
    FlopType.DIV        [x/y]           :   5.50000
    FlopType.SQRT       [sqrt(x)]       :   7.50000
    FlopType.EXP2       [2^x]           :  16.00000
    FlopType.EXP        [e^x]           :  18.00000
    FlopType.LOG        [log(x)]        :  18.00000
    FlopType.EXP10      [10^x]          :  22.00000
    FlopType.LOG2       [log2(x)]       :  22.00000
    FlopType.LOG10      [log10(x)]      :  24.00000
    FlopType.COS        [cos(x)]        :  30.00000
    FlopType.SIN        [sin(x)]        :  30.00000
    FlopType.POW        [x^y]           :  40.00000
    FlopType.TAN        [tan(x)]        :  40.00000
    FlopType.CBRT       [cbrt(x)]       :  45.00000
}
```
Note that these weights are rounded up to the ~10% closest semi-round number, reflecting a balance between accuracy and readability,
while conveying the message that these weights should be used as approximations only.  See further down for the different rounding modes.

These weights will be used by default when extracting total weighted flop costs:

```python
import math
from counted_float import CountedFloat, FlopCountingContext


cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 + cf2
    _ = cf1 ** cf2
    _ = math.log2(cf2)
    
flop_counts = ctx.flop_counts()
total_cost = flop_counts.total_weighted_cost()  # 1 + 40 + 22 = 63
```
Note that the `total_weighted_cost` method will use the default flop weights as returned by `get_flop_weights()`.  This can be
overridden by either configuring different flop weights (see next section) or by setting the `weights` argument of the `total_weighted_cost()` method.


## 2.4. Configuring FLOP weights

We showed earlier that the `get_flop_weights()` function returns the default FLOP weights.  We can change this by
using the `set_flop_weights()` function, which takes a `FlopWeights` object as an argument.  This way we can configure
flop weights that might be obtained using benchmarks run on the target hardware (see later sections).

```python
from counted_float.config import set_active_flop_weights
from counted_float import FlopWeights

set_active_flop_weights(weights=FlopWeights(...))  # insert own weights here
```
## 2.5. Inspecting built-in data

### 2.5.1. Default, pre-aggregated flop weights

Built-in flop weights can be inspected using the following functions:

```python
from counted_float.config import get_default_consensus_flop_weights

>>> get_default_consensus_flop_weights(rounding_mode=None).show()

{
    FlopType.MINUS      [-x]            :   0.43688
    FlopType.ABS        [abs(x)]        :   0.71585
    FlopType.COMP       [x<=y]          :   0.97866
    FlopType.SUB        [x-y]           :   0.99565
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.MUL        [x*y]           :   1.39506
    FlopType.RND        [round]         :   1.78130
    FlopType.F2I        [float->int]    :   1.91125
    FlopType.I2F        [int->float]    :   1.91839
    FlopType.DIV        [x/y]           :   5.53385
    FlopType.SQRT       [sqrt(x)]       :   7.37309
    FlopType.EXP2       [2^x]           :  15.79616
    FlopType.EXP        [e^x]           :  17.45201
    FlopType.LOG        [log(x)]        :  18.93143
    FlopType.LOG2       [log2(x)]       :  22.29433
    FlopType.EXP10      [10^x]          :  22.93876
    FlopType.LOG10      [log10(x)]      :  24.56277
    FlopType.SIN        [sin(x)]        :  30.28970
    FlopType.COS        [cos(x)]        :  31.27413
    FlopType.POW        [x^y]           :  41.65022
    FlopType.TAN        [tan(x)]        :  41.99495
    FlopType.CBRT       [cbrt(x)]       :  44.15405
}
```
There are 3 rounding modes:
- `None` -> no rounding
- `"nearest_int"` -> round up/down to nearest integer, with a minimum of 1
- `"10%"` -> round to nearest semi-round number within ~10% (default)


The default weights that are configured out-of-the-box in the package are the integer-rounded `consensus` weights.

### 2.5.2. Custom-aggregated flop weights

We can retrieve built-in flop weights in a more fine-grained manner, by custom filtering and the aggregating them with
the geometric mean.

```python
from counted_float.config import get_builtin_flop_weights

>>> get_builtin_flop_weights(key_filter="arm").show()

{
    FlopType.COMP       [x<=y]          :   0.65000
    FlopType.MINUS      [-x]            :   0.90000
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   1.00000
    FlopType.ABS        [abs(x)]        :   1.10000
    FlopType.F2I        [float->int]    :   1.50000
    FlopType.MUL        [x*y]           :   1.50000
    FlopType.I2F        [int->float]    :   1.60000
    FlopType.RND        [round]         :   1.60000
    FlopType.DIV        [x/y]           :   6.00000
    FlopType.SQRT       [sqrt(x)]       :   7.50000
    FlopType.EXP2       [2^x]           :  16.00000
    FlopType.EXP        [e^x]           :  18.00000
    FlopType.LOG        [log(x)]        :  20.00000
    FlopType.LOG2       [log2(x)]       :  20.00000
    FlopType.EXP10      [10^x]          :  24.00000
    FlopType.LOG10      [log10(x)]      :  24.00000
    FlopType.COS        [cos(x)]        :  33.00000
    FlopType.SIN        [sin(x)]        :  33.00000
    FlopType.POW        [x^y]           :  40.00000
    FlopType.CBRT       [cbrt(x)]       :  45.00000
    FlopType.TAN        [tan(x)]        :  45.00000
}
```

# 3. Benchmarking

If the package is installed with the optional `numba` dependency, it provides the ability to micro-benchmark 
floating point operations as follows:

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

## 4. Installing the package as a command-line tool

An alternative way of using (parts) of the functionality is installing the package as a stand-alone command-line tool
using `uv` or `pipx`:

```
uv tool install git+https://github.com/bertpl/counted-float@main[numba,cli]         # latest official release
uv tool install git+https://github.com/bertpl/counted-float@develop[numba,cli]      # or latest develop version
```
This installs the `counted_float` command-line tool, which can be used to e.g. run flops benchmarks.

## 4.1. Running benchmarks

```
counted_float benchmark
```
after which the results will be shown as .json.

## 4.2. Show built-in data

```
[~] counted_float show-data
                                                                        MINUS       ABS      COMP       SUB       ADD       MUL       RND       F2I       I2F       DIV      SQRT      EXP2       EXP       LOG      LOG2     EXP10     LOG10       SIN       COS       POW       TAN      CBRT
ALL                                                                      0.44      0.72      0.98      1.00      1.00      1.40      1.78      1.91      1.92      5.53      7.37     15.80     17.45     18.93     22.29     22.94     24.56     30.29     31.27     41.65     41.99     44.15
 ├─arm                                                                   0.89      1.05      0.64      1.01      1.00      1.50      1.61      1.49      1.59      6.15      7.60     15.98     18.57     19.60     20.86     23.30     24.26     32.32     34.08     42.28     42.85     44.97
 │  ├─v8_x                                                               0.83      1.00      0.67      1.01      1.00      1.48      1.50      1.56      1.91      5.90      7.42     15.45     17.86     19.06     20.80     22.92     22.90     32.43     33.47     41.19     42.99     44.71
 │  │  ├─benchmarks                                                      0.70      1.01      0.45      1.01      1.00      1.46      1.50        /         /       4.65      6.68     13.93     16.10     17.18     18.75     20.66     20.65     29.23     30.17     37.13     38.76     40.30
 │  │  │  ├─apple_m1_github_actions                                      0.86      0.86      1.73      1.06      1.00      1.48      1.22        /         /       4.07      5.70     15.50     16.98     17.33     20.52     19.61     17.95     29.86     31.59     38.67     38.97     41.44
 │  │  │  ├─apple_m3_max_mbp16                                           0.90      0.90      1.64      1.00      1.00      1.40      1.25        /         /       4.00      5.28     16.69     17.42     17.59     18.15     21.06     17.31     28.77     29.17     37.93     39.04     39.48
 │  │  │  ├─apple_m3_mba15                                               0.90      0.90      1.68      1.00      1.00      1.53      1.24        /         /       4.06      5.27     16.68     17.43     17.56     18.09     21.07     17.29     28.63     29.06     38.46     32.32     39.43
 │  │  │  ├─aws_graviton_2_neoverse_n1_ec2_m6g_xlarge                    0.46      1.47      0.38      1.00      1.00      1.38      2.01        /         /       5.42      8.76     10.21     14.17     15.98     17.91     22.65     25.25     28.68     29.63     33.95     41.90     40.25
 │  │  │  └─aws_graviton_3_neoverse_v1_ec2_m7g_xlarge                    0.51      1.00      0.01      1.00      1.00      1.50      1.99        /         /       6.03      9.58     11.89     14.81     17.49     19.20     19.09     27.67     30.26     31.49     36.85     42.45     40.96
 │  │  └─specs                                                           1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.73      2.12      7.50      8.25        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_cortex_a76                                               1.00      1.00      1.00      1.00      1.00      1.50      1.50      2.00      3.00      7.50      8.50        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_cortex_x1                                                1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      7.50      8.00        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_neoverse_n1                                              1.00      1.00      1.00      1.00      1.00      1.50      1.50      2.00      3.00      7.50      8.50        /         /         /         /         /         /         /         /         /         /         / 
 │  │     └─arm_neoverse_v1                                              1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      7.50      8.00        /         /         /         /         /         /         /         /         /         /         / 
 │  ├─v9_0                                                               0.74      1.00      0.25      1.00      1.00      1.51      1.80      1.27      1.27      6.78      8.83     14.32     17.90     20.66     22.09     24.04     32.41     35.53     37.31     44.86     52.70     48.30
 │  │  ├─benchmarks                                                      0.54      1.00      0.06      1.00      1.00      1.52      2.16        /         /       6.14      9.75     12.12     15.15     17.49     18.70     20.35     27.44     30.08     31.59     37.98     44.62     40.89
 │  │  │  ├─aws_graviton_4_neoverse_v2_ec2_m8g_xlarge                    0.52      1.00      0.01      1.00      1.00      1.50      2.05        /         /       6.04      9.49     12.66     14.40     17.66     18.54     19.86     27.12     28.76     30.11     36.90     42.70     38.65
 │  │  │  └─azure_cobalt_100_neoverse_n2_github_actions                  0.57      1.00      0.33      1.00      1.00      1.53      2.28        /         /       6.23     10.02     11.61     15.94     17.33     18.87     20.85     27.76     31.46     33.15     39.09     46.62     43.26
 │  │  └─specs                                                           1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      7.50      8.00        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_cortex_x2                                                1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      7.50      8.00        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_cortex_x3                                                1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      7.50      8.00        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_neoverse_n2                                              1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      7.50      8.00        /         /         /         /         /         /         /         /         /         /         / 
 │  │     └─arm_neoverse_v2                                              1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      7.50      8.00        /         /         /         /         /         /         /         /         /         /         / 
 │  └─v9_2                                                               1.16      1.16      1.55      1.02      1.00      1.51      1.55      1.66      1.66      5.80      6.70     18.44     20.04     19.11     19.75     22.96     19.23     29.29     31.69     40.89     34.73     42.11
 │     ├─benchmarks                                                      1.35      1.35      2.40      1.03      1.00      1.51      1.84        /         /       5.32      7.10     20.38     22.15     21.13     21.83     25.38     21.25     32.38     35.03     45.20     38.39     46.55
 │     │  └─apple_m4_pro_mbp16                                           1.35      1.35      2.40      1.03      1.00      1.51      1.84        /         /       5.32      7.10     20.38     22.15     21.13     21.83     25.38     21.25     32.38     35.03     45.20     38.39     46.55
 │     └─specs                                                           1.00      1.00      1.00      1.00      1.00      1.50      1.31      1.50      1.50      6.33      6.33        /         /         /         /         /         /         /         /         /         /         / 
 │        ├─arm_cortex_x4                                                1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      6.50      6.50        /         /         /         /         /         /         /         /         /         /         / 
 │        ├─arm_cortex_x925                                              1.00      1.00      1.00      1.00      1.00      1.50      1.00      1.50      1.50      6.00      6.00        /         /         /         /         /         /         /         /         /         /         / 
 │        └─arm_neoverse_v3                                              1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      6.50      6.50        /         /         /         /         /         /         /         /         /         /         / 
 └─x86                                                                   0.21      0.49      1.50      0.98      1.00      1.30      1.97      2.46      2.31      4.98      7.15     15.62     16.40     18.29     23.83     22.58     24.87     28.39     28.70     41.03     41.15     43.35
    ├─amd                                                                0.25      0.45      1.52      0.99      1.00      1.17      1.22      2.39      2.51      4.74      7.38     18.22     16.50     17.98     24.59     23.73     24.13     28.04     28.30     42.41     40.31     45.11
    │  ├─2017_zen1                                                       0.34      0.34      1.16      1.00      1.00      1.29      1.34      3.07      3.07      4.18      6.44     63.95     19.71     17.05     32.24     43.83     18.79     30.58     30.27     57.99     39.24     66.55
    │  │  ├─benchmarks                                                   0.35      0.35      0.58      1.01      1.00      1.24      1.34        /         /       4.03      6.23     58.90     18.16     15.70     29.69     40.37     17.30     28.16     27.88     53.41     36.14     61.29
    │  │  │  └─amd_ryzen_1700x                                           0.35      0.35      0.58      1.01      1.00      1.24      1.34        /         /       4.03      6.23     58.90     18.16     15.70     29.69     40.37     17.30     28.16     27.88     53.41     36.14     61.29
    │  │  └─other                                                        0.33      0.33      2.33      1.00      1.00      1.33      1.33      3.33      3.33      4.33      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  │     └─analysis_uops_info_zen1+                                  0.33      0.33      2.33      1.00      1.00      1.33      1.33      3.33      3.33      4.33      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  ├─2020_zen3                                                       0.18      0.34      1.16      1.00      1.00      0.98      1.00      2.17      2.34      4.36      6.76     11.69     15.85     16.99     22.46     19.32     21.13     24.05     24.07     38.13     38.04     39.06
    │  │  ├─benchmark                                                    0.10      0.34      0.68      1.00      1.00      1.00      1.00        /         /       4.30      6.86     10.33     14.01     15.02     19.86     17.08     18.69     21.26     21.28     33.72     33.63     34.54
    │  │  │  ├─amd_epyc_7763_linux_github                                0.10      0.34      0.68      1.00      1.00      1.00      1.00        /         /       4.31      6.86     10.35     11.79     15.35     14.36     14.53     22.21     22.45     22.86     30.57     33.34     31.25
    │  │  │  └─amd_epyc_7763_windows_github                              0.10      0.34      0.68      1.00      1.00      1.00      1.00        /         /       4.28      6.86     10.32     16.65     14.70     27.48     20.08     15.72     20.14     19.82     37.19     33.92     38.17
    │  │  └─other                                                        0.33      0.33      1.97      1.00      1.00      0.95      1.00      2.45      2.65      4.42      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  │     ├─analysis_agner_fog_r7_5800x                               0.33      0.33      1.67      1.00      1.00        /       1.00      2.00      2.33      4.50      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  │     └─analysis_uops_info_zen3                                   0.33      0.33      2.33      1.00      1.00      1.00      1.00      3.00      3.00      4.33      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  ├─2022_zen4                                                       0.15      0.33      1.41      0.99      1.00      0.99      1.00      1.85      1.78      4.41      6.92     10.77     12.47     17.12     20.49     15.83     25.03     24.11     24.56     32.21     35.99     33.32
    │  │  ├─benchmark                                                    0.07      0.33      1.57      0.97      1.00      0.98      0.99        /         /       4.49      6.95      9.97     11.55     15.86     18.98     14.66     23.19     22.34     22.75     29.84     33.34     30.87
    │  │  │  └─amd_epyc_9r14_ec2_m7a_xlarge                              0.07      0.33      1.57      0.97      1.00      0.98      0.99        /         /       4.49      6.95      9.97     11.55     15.86     18.98     14.66     23.19     22.34     22.75     29.84     33.34     30.87
    │  │  └─other                                                        0.33      0.33      1.28      1.00      1.00      1.01      1.00      2.00      1.92      4.33      6.89        /         /         /         /         /         /         /         /         /         /         / 
    │  │     ├─analysis_agner_fog_r9_7900x                               0.33      0.33      1.33      1.00      1.00        /       1.00      2.00      2.00      4.33      7.00        /         /         /         /         /         /         /         /         /         /         / 
    │  │     ├─analysis_uops_info_zen4                                   0.33      0.33      2.33      1.00      1.00      1.00      1.00      3.00      2.67      4.33      7.00        /         /         /         /         /         /         /         /         /         /         / 
    │  │     └─specs_amd                                                 0.33      0.33      0.67      1.00      1.00      1.00      1.00      1.33      1.33      4.33      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  └─2024_zen5                                                       0.39      1.04      2.83      0.95      1.00      1.50      1.68      2.64      3.08      6.31      9.84     13.71     19.04     21.09     24.62     23.64     34.12     34.84     35.83     45.40     49.16     47.78
    │     ├─benchmark                                                    0.21      1.53      2.95      0.91      1.00      1.36      1.87        /         /       6.12      9.69     13.33     18.50     20.50     23.94     22.98     33.17     33.87     34.83     44.14     47.79     46.45
    │     │  └─amd_epyc_9r45_ec2_m8a_xlarge                              0.21      1.53      2.95      0.91      1.00      1.36      1.87        /         /       6.12      9.69     13.33     18.50     20.50     23.94     22.98     33.17     33.87     34.83     44.14     47.79     46.45
    │     └─other                                                        0.71      0.71      2.72      1.00      1.00      1.66      1.50      2.72      3.17      6.50     10.00        /         /         /         /         /         /         /         /         /         /         / 
    │        ├─analysis_agner_fog_r7_9800x3d                             1.00      1.00      3.00      1.00      1.00        /       1.50      3.00      3.50      6.50     10.00        /         /         /         /         /         /         /         /         /         /         / 
    │        └─specs_amd                                                 0.50      0.50        /       1.00      1.00      1.50      1.50        /         /       6.50     10.00        /         /         /         /         /         /         /         /         /         /         / 
    └─intel                                                              0.18      0.53      1.47      0.98      1.00      1.45      3.17      2.53      2.14      5.23      6.93     13.38     16.30     18.60     23.09     21.50     25.64     28.75     29.11     39.70     42.01     41.67
       ├─2017_coffee_lake_gen_8                                          0.14      0.40      1.12      0.98      1.00      1.03      1.99      1.69      1.69      3.54      4.56     10.27     16.31     12.42     19.10     21.50     12.84     20.48     20.47     32.65     28.21     35.74
       │  ├─benchmarks                                                   0.08      0.63      1.73      0.96      1.00      1.05      1.99        /         /       3.45      4.78     10.69     16.98     12.92     19.88     22.38     13.37     21.31     21.31     33.99     29.36     37.20
       │  │  ├─intel_i7_8550U_windows                                    0.08      0.44      1.69      1.01      1.00      1.01      2.00        /         /       3.15      4.79      7.02     15.44     11.99     30.07     21.33     13.00     17.80     17.21     32.36     28.09     35.06
       │  │  └─intel_i7_8700B_macos_github_actions                       0.08      0.91      1.77      0.92      1.00      1.10      1.97        /         /       3.78      4.77     16.30     18.68     13.93     13.15     23.47     13.74     25.51     26.38     35.70     30.68     39.48
       │  └─other                                                        0.25      0.25      0.73      1.00      1.00      1.00      2.00      1.62      1.62      3.62      4.36        /         /         /         /         /         /         /         /         /         /         / 
       │     ├─analysis_agner_fog_coffee_lake                            0.25      0.25        /       1.00      1.00      1.00      2.00      1.50      1.50      3.50      4.00        /         /         /         /         /         /         /         /         /         /         / 
       │     └─analysis_uops_info_coffee_lake                            0.25      0.25      0.75      1.00      1.00      1.00      2.00      1.75      1.75      3.75      4.75        /         /         /         /         /         /         /         /         /         /         / 
       ├─2019_sunny_cove_gen_10                                          0.10      0.33      0.92      0.95      1.00      0.98      1.94      1.60      1.60      3.58      4.54     12.27      9.43     14.01     17.18     13.39     20.23     19.23     19.83     28.71     29.72     28.95
       │  ├─benchmarks                                                   0.04      0.44      1.30      0.91      1.00      1.00      1.89        /         /       3.50      4.60     11.82      9.08     13.49     16.55     12.90     19.48     18.52     19.09     27.65     28.63     27.88
       │  │  └─intel_xeon_8375c_ice_lake_ec2_m6i_xlarge                  0.04      0.44      1.30      0.91      1.00      1.00      1.89        /         /       3.50      4.60     11.82      9.08     13.49     16.55     12.90     19.48     18.52     19.09     27.65     28.63     27.88
       │  └─other                                                        0.25      0.25      0.66      1.00      1.00      0.97      2.00      1.66      1.66      3.66      4.49        /         /         /         /         /         /         /         /         /         /         / 
       │     ├─analysis_agner_fog_ice_lake                               0.25      0.25      0.50      1.00      1.00        /       2.00      1.50      1.50      3.50      4.00        /         /         /         /         /         /         /         /         /         /         / 
       │     ├─analysis_uops_info_ice_lake                               0.25      0.25      0.75      1.00      1.00      1.00      2.00      1.75      1.75      3.75      4.75        /         /         /         /         /         /         /         /         /         /         / 
       │     └─analysis_uops_info_tiger_lake                             0.25      0.25      0.75      1.00      1.00      1.00      2.00      1.75      1.75      3.75      4.75        /         /         /         /         /         /         /         /         /         /         / 
       ├─2021_golden_cove_gen_12                                         0.23      0.64      1.76      0.99      1.00      1.80      4.05      3.11      2.63      6.34      8.58     14.98     18.37     21.93     25.63     24.02     32.77     34.73     35.06     44.04     50.72     46.59
       │  ├─benchmarks                                                   0.13      0.99      2.52      0.98      1.00      1.99      5.03        /         /       6.80      9.74     16.28     19.97     23.84     27.86     26.11     35.63     37.76     38.12     47.88     55.14     50.65
       │  │  └─intel_xeon_8488c_sapphire_rapids_ec2_m7i_xlarge           0.13      0.99      2.52      0.98      1.00      1.99      5.03        /         /       6.80      9.74     16.28     19.97     23.84     27.86     26.11     35.63     37.76     38.12     47.88     55.14     50.65
       │  └─other                                                        0.41      0.41      1.22      1.00      1.00      1.63      3.27      2.86      2.42      5.92      7.55        /         /         /         /         /         /         /         /         /         /         / 
       │     ├─analysis_uops_info_alder_lake_p                           0.33      0.33      1.00      1.00      1.00      1.33      2.67      2.33      2.33      5.00      6.33        /         /         /         /         /         /         /         /         /         /         / 
       │     └─specs_intel                                               0.50      0.50      1.50      1.00      1.00      2.00      4.00      3.50      2.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
       ├─2022_raptor_cove_gen_13_14                                      0.26      0.71      1.96      1.00      1.00      2.00      4.51      3.55      2.53      7.00      9.49     15.73     19.93     24.00     28.64     26.02     35.73     37.86     38.33     49.02     55.79     51.16
       │  ├─benchmarks                                                   0.13      1.00      2.55      1.00      1.00      2.00      5.08        /         /       7.00     10.00     15.95     20.20     24.33     29.03     26.37     36.21     38.37     38.85     49.69     56.55     51.86
       │  │  └─intel_xeon_8559c_emerald_rapids_ec2_i7i_xlarge            0.13      1.00      2.55      1.00      1.00      2.00      5.08        /         /       7.00     10.00     15.95     20.20     24.33     29.03     26.37     36.21     38.37     38.85     49.69     56.55     51.86
       │  └─other                                                        0.50      0.50      1.50      1.00      1.00      2.00      4.00      3.50      2.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
       │     └─specs_intel                                               0.50      0.50      1.50      1.00      1.00      2.00      4.00      3.50      2.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
       └─2023_redwood_cove_ultra_1                                       0.24      0.71      1.95      0.99      1.00      1.73      4.51      3.46      2.47      6.97      9.47     14.44     20.41     24.32     27.29     25.53     36.40     37.92     38.32     48.75     55.19     50.95
          ├─benchmarks                                                   0.12      1.01      2.53      0.98      1.00      1.50      5.09        /         /       6.94      9.96     14.28     20.19     24.06     26.99     25.26     36.01     37.51     37.91     48.22     54.60     50.40
          │  └─intel_xeon_6975p_granite_rapids_ec2_m8i_xlarge            0.12      1.01      2.53      0.98      1.00      1.50      5.09        /         /       6.94      9.96     14.28     20.19     24.06     26.99     25.26     36.01     37.51     37.91     48.22     54.60     50.40
          └─other                                                        0.50      0.50      1.50      1.00      1.00      2.00      4.00      3.50      2.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
             └─specs_intel                                               0.50      0.50      1.50      1.00      1.00      2.00      4.00      3.50      2.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
 

```

## 4.2. Test performance of `CountedFloat` vs `float`

```
[~] counted_float benchmark-counted-float
```
See next section for results.

# 5. Performance impact

Obviously, using `CountedFloat` instead of regular `float` will have a performance impact due to the overhead of counting operations.
It is not advised to use `CountedFloat` for production code, but just for research code for which you want to estimate the floating-point operation count.

Micro-benchmarking of a bisection algorithm using `counted_float benchmark-counted-float` teaches us this:
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

# 6. Known limitations

- currently any non-Python-built-in math operations are not counted (e.g. `numpy`)
- not all Python built-in math operations are counted (e.g. hyperbolic functions)
- flop weights should be taken with a grain of salt and should only provide relative ballpark estimates w.r.t computational complexity.  Production implementations in a compiled language could have vastly differing performance depending on cpu cache sizes, branch prediction misses, compiler optimizations using vector operations (AVX etc...), etc...
 
# Appendix A - Flop counting / analysis details

This appendix provides detailed information about how each floating-point operation (FLOP) type is counted and analyzed in the `counted-float` package. For each flop type, you will find:
- Relevant scalar instructions for ARM (v8+) and x86 (SSE2+)
- Python operations that are counted for this flop type
- Python operations that are *not* counted for this flop type

## Flop Types

### FlopType.ABS (`abs(x)`)
- Relevant CPU instructions
  - **ARM:** `FABS`
  - **x86:** `ANDPD`
- **Counted Python operations:** `abs(x)` where `x` is a `CountedFloat`
- **Not counted:** `numpy.abs`, complex abs, abs on non-CountedFloat

### FlopType.MINUS (`-x`)
- Relevant CPU instructions
  - **ARM:** `FNEG`
  - **x86:** `XORPD`
- **Counted Python operations:** Unary minus (`-x`) for `CountedFloat`
- **Not counted:** Negation on non-CountedFloat, numpy negation

### FlopType.COMP (`x<=y`, `x>y`, `x==y`, `x==0.0`, ...)
- Relevant CPU instructions
  - **ARM:** `FCMP`
  - **x86:** `(U)COMISD`
- **Counted Python operations:** `x == y`, `x != y`, `x <= y`, ... and `min(x,y)`, `max(x,y)` for `CountedFloat`
- **Not counted:** Comparisons on non-CountedFloat, numpy comparisons

### FlopType.RND (`round`)
- Relevant CPU instructions
  - **ARM:** `FRINT`
  - **x86:** `ROUNDSD`
- **Counted Python operations:** `round(x, 0)` for `CountedFloat` (returns float)
- **Not counted:** `numpy.round`, rounding with decimals, rounding on non-CountedFloat

### FlopType.F2I (`float->int`)
- Relevant CPU instructions
  - **ARM:** `FCVTZS`
  - **x86:** `CVTSD2SI`
- **Counted Python operations:** `int(x)`, `math.floor(x)`, `math.ceil(x)`, `math.trunc(x)`, `round(x)` for `CountedFloat` (returns int)
- **Not counted:** Conversions on non-CountedFloat, numpy conversions

### FlopType.I2F (`int->float`)
- Relevant CPU instructions
  - **ARM:** `SCVTF`
  - **x86:** `CVTSI2SD`
- **Counted Python operations:** Construction of `CountedFloat` from int, any binary operation where one operand is an int and the other a `CountedFloat` (e.g., `x + 3`, `3 * x`, etc.)
- **Not counted:** `float(n)`, unitary operations (e.g. `math.sqrt` on integers -> convert to `CountedFloat` first)

### FlopType.ADD (`x+y`)
- Relevant CPU instructions
  - **ARM:** `FADD`
  - **x86:** `ADDSD`
- **Counted Python operations:** `x + y` or `y + x` for `CountedFloat`
- **Not counted:** Addition on non-CountedFloat, numpy addition

### FlopType.SUB (`x-y`)
- Relevant CPU instructions
  - **ARM:** `FSUB`
  - **x86:** `SUBSD`
- **Counted Python operations:** `x - y` or `y - x` for `CountedFloat`
- **Not counted:** Subtraction on non-CountedFloat, numpy subtraction

### FlopType.MUL (`x*y`)
- Relevant CPU instructions
  - **ARM:** `FMUL`
  - **x86:** `MULSD`
- **Counted Python operations:** `x * y` or `y * x` for `CountedFloat`
- **Not counted:** Multiplication on non-CountedFloat, numpy multiplication

### FlopType.DIV (`x/y`)
- Relevant CPU instructions
  - **ARM:** `FDIV`
  - **x86:** `DIVSD`
- **Counted Python operations:** `x / y` or `y / x` for `CountedFloat`
- **Not counted:** Division on non-CountedFloat, numpy division

### FlopType.SQRT (`sqrt(x)`)
- Relevant CPU instructions
  - **ARM:** `FSQRT`
  - **x86:** `SQRTSD`
- **Counted Python operations:** `math.sqrt(x)` for `CountedFloat`
- **Not counted:** `numpy.sqrt`, sqrt on non-CountedFloat

### FlopType.CBRT (`cbrt(x)`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.cbrt(x)` for `CountedFloat`
- **Not counted:** `numpy.cbrt`, cbrt on non-CountedFloat

### FlopType.EXP (`e^x`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.exp(x)` for `CountedFloat`
- **Not counted:** `math.exp(x)` on non-CountedFloat, `numpy.exp`, `math.expm1`, `math.e ** x`

### FlopType.EXP2 (`2^x`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `2 ** x`, `pow(2, x)` or `math.exp2(x)` for `CountedFloat`
- **Not counted:** `exp2` on non-CountedFloat, `numpy.exp2`

### FlopType.EXP10 (`10^x`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `10 ** x`, `pow(10, x)` for `CountedFloat`
- **Not counted:** `10 ** x` on non-CountedFloat

### FlopType.LOG (`log(x)`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.log(x)` for `CountedFloat`
- **Not counted:** `numpy.log`, log on non-CountedFloat

### FlopType.LOG2 (`log2(x)`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.log2(x)` for `CountedFloat`
- **Not counted:** `numpy.log2`, log2 on non-CountedFloat

### FlopType.LOG10 (`log10(x)`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.log10(x)` for `CountedFloat`
- **Not counted:** `numpy.log10`, log10 on non-CountedFloat

### FlopType.POW (`x^y`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `x ** y`, `pow(x, y)` for `CountedFloat`
- **Not counted:** `pow` on non-CountedFloat, `numpy.pow`

### FlopType.SIN (`sin(x)`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.sin(x)` for `CountedFloat`
- **Not counted:** `sin` on non-CountedFloat, `numpy.sin`

### FlopType.COS (`cos(x)`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.cos(x)` for `CountedFloat`
- **Not counted:** `cos` on non-CountedFloat, `numpy.cos`

### FlopType.TAN (`tan(x)`)
- Relevant CPU instructions
  - **ARM:** (software)
  - **x86:** (software)
- **Counted Python operations:** `math.tan(x)` for `CountedFloat`
- **Not counted:** `tan` on non-CountedFloat, `numpy.tan