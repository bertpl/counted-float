<!--START_SECTION:images-->
![shields.io-python-versions](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![genbadge-test-count](https://bertpl.github.io/counted-float/version_artifacts/v0.9.6/badge-test-count.svg)
![genbadge-test-coverage](https://bertpl.github.io/counted-float/version_artifacts/v0.9.6/badge-coverage.svg)
![counted_float logo](https://bertpl.github.io/counted-float/version_artifacts/v0.9.6/splash.webp)
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
    FlopType.ABS        [abs(x)]        :    1
    FlopType.MINUS      [-x]            :    1
    FlopType.COMP       [x<=y]          :    1
    FlopType.RND        [round]         :    2
    FlopType.F2I        [float->int]    :    2
    FlopType.I2F        [int->float]    :    2
    FlopType.ADD        [x+y]           :    1
    FlopType.SUB        [x-y]           :    1
    FlopType.MUL        [x*y]           :    1
    FlopType.DIV        [x/y]           :    5
    FlopType.SQRT       [sqrt(x)]       :    6
    FlopType.CBRT       [cbrt(x)]       :   42
    FlopType.EXP        [e^x]           :   19
    FlopType.EXP2       [2^x]           :   29
    FlopType.EXP10      [10^x]          :   23
    FlopType.LOG        [log(x)]        :   19
    FlopType.LOG2       [log2(x)]       :   24
    FlopType.LOG10      [log10(x)]      :   19
    FlopType.POW        [x^y]           :   62
    FlopType.SIN        [sin(x)]        :   32
    FlopType.COS        [cos(x)]        :   31
    FlopType.TAN        [tan(x)]        :   34
}
```
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
total_cost = flop_counts.total_weighted_cost()  # 1 + 62 + 24 = 87
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

>>> get_default_consensus_flop_weights(rounded=False).show()

{
    FlopType.ABS        [abs(x)]        :   0.63673
    FlopType.MINUS      [-x]            :   0.64396
    FlopType.COMP       [x<=y]          :   1.20756
    FlopType.RND        [round]         :   1.54041
    FlopType.F2I        [float->int]    :   1.99099
    FlopType.I2F        [int->float]    :   1.84601
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   1.00586
    FlopType.MUL        [x*y]           :   1.37238
    FlopType.DIV        [x/y]           :   5.07465
    FlopType.SQRT       [sqrt(x)]       :   5.90559
    FlopType.CBRT       [cbrt(x)]       :  42.39375
    FlopType.EXP        [e^x]           :  18.58228
    FlopType.EXP2       [2^x]           :  28.88672
    FlopType.EXP10      [10^x]          :  22.86839
    FlopType.LOG        [log(x)]        :  18.89135
    FlopType.LOG2       [log2(x)]       :  24.34792
    FlopType.LOG10      [log10(x)]      :  18.55085
    FlopType.POW        [x^y]           :  61.79155
    FlopType.SIN        [sin(x)]        :  31.91490
    FlopType.COS        [cos(x)]        :  30.79295
    FlopType.TAN        [tan(x)]        :  34.37970
}
```

The default weights that are configured out-of-the-box in the package are the integer-rounded `consensus` weights.

### 2.5.2. Custom-aggregated flop weights

We can retrieve built-in flop weights in a more fine-grained manner, by custom filtering and the aggregating them with
the geometric mean.

```python
from counted_float.config import get_builtin_flop_weights

>>> get_builtin_flop_weights(key_filter="arm").show()

{
    FlopType.ABS        [abs(x)]        :   0.97313
    FlopType.MINUS      [-x]            :   0.99098
    FlopType.COMP       [x<=y]          :   1.03987
    FlopType.RND        [round]         :   1.35111
    FlopType.F2I        [float->int]    :   1.52648
    FlopType.I2F        [int->float]    :   1.63320
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   1.00058
    FlopType.MUL        [x*y]           :   1.44952
    FlopType.DIV        [x/y]           :   5.00897
    FlopType.SQRT       [sqrt(x)]       :   5.15597
    FlopType.CBRT       [cbrt(x)]       :  39.30448
    FlopType.EXP        [e^x]           :  17.22817
    FlopType.EXP2       [2^x]           :  15.82232
    FlopType.EXP10      [10^x]          :  21.20195
    FlopType.LOG        [log(x)]        :  17.51472
    FlopType.LOG2       [log2(x)]       :  18.32529
    FlopType.LOG10      [log10(x)]      :  17.19903
    FlopType.POW        [x^y]           :  47.63289
    FlopType.SIN        [sin(x)]        :  29.58923
    FlopType.COS        [cos(x)]        :  28.54904
    FlopType.TAN        [tan(x)]        :  31.87442
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

>>> results.flop_weights.show() 

{
    FlopType.ABS        [abs(x)]        :   0.90556
    FlopType.MINUS      [-x]            :   0.90089
    FlopType.COMP       [x<=y]          :   1.67297
    FlopType.RND        [round]         :   1.24118
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   0.99928
    FlopType.MUL        [x*y]           :   1.52656
    FlopType.DIV        [x/y]           :   4.06589
    FlopType.SQRT       [sqrt(x)]       :   5.26487
    FlopType.CBRT       [cbrt(x)]       :  39.49190
    FlopType.EXP        [e^x]           :  17.34508
    FlopType.EXP2       [2^x]           :  16.70475
    FlopType.EXP10      [10^x]          :  21.03351
    FlopType.LOG        [log(x)]        :  17.59412
    FlopType.LOG2       [log2(x)]       :  18.08932
    FlopType.LOG10      [log10(x)]      :  17.27955
    FlopType.POW        [x^y]           :  38.32044
    FlopType.SIN        [sin(x)]        :  28.67006
    FlopType.COS        [cos(x)]        :  29.11818
    FlopType.TAN        [tan(x)]        :  32.28703
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

                                                       ABS     MINUS       ADD       SUB      COMP       MUL       RND       I2F       F2I       DIV      SQRT     LOG10       EXP       LOG     EXP10      LOG2      EXP2       COS       SIN       TAN      CBRT       POW
ALL                                                   0.64      0.64      1.00      1.01      1.21      1.37      1.54      1.85      1.99      5.07      5.91     18.55     18.58     18.89     22.87     24.35     28.89     30.79     31.91     34.38     42.39     61.79
 ├─arm                                                0.97      0.99      1.00      1.00      1.04      1.45      1.35      1.63      1.53      5.01      5.16     17.20     17.23     17.51     21.20     18.33     15.82     28.55     29.59     31.87     39.30     47.63
 │  ├─v8_x                                            0.92      0.97      1.00      1.00      1.12      1.35      1.25      1.94      1.58      3.88      4.09     16.56     16.59     16.86     20.41     17.64     15.23     27.48     28.49     30.69     37.84     45.86
 │  │  ├─benchmarks                                   0.85      0.95      1.00      1.00      1.26      1.22      1.05        /         /       2.93      3.12     15.11     15.14     15.39     18.63     16.10     13.90     25.09     26.00     28.01     34.54     41.85
 │  │  │  ├─m3_max_macbook_pro_16                     0.80      1.00      1.00      1.01      1.01      1.01      0.89        /         /       2.19      1.85        /         /         /         /      14.40     11.59        /         /         /         /      46.48
 │  │  │  └─m3_max_macbook_pro_16_v2                  0.90      0.90      1.00      1.00      1.58      1.47      1.24        /         /       3.93      5.25     17.23     17.26     17.55     21.24     18.01     16.68     28.60     29.64     31.93     39.38     37.68
 │  │  └─specs                                        1.00      1.00      1.00      1.00      1.00      1.50      1.50      2.12      1.73      5.12      5.37        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_v8_cortex_a76                         1.00      1.00      1.00      1.00      1.00      1.50      1.50      3.00      2.00      5.12      5.45        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_v9_cortex_n1                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      3.00      2.00      5.12      5.45        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_v9_cortex_v1                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  │     └─arm_v9_cortex_x1                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  ├─v9_0                                            1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  │  └─specs                                        1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_v9_cortex_n2                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_v9_cortex_v2                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  │     ├─arm_v9_cortex_x2                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  │     └─arm_v9_cortex_x3                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      5.12      5.29        /         /         /         /         /         /         /         /         /         /         / 
 │  └─v9_2                                            1.00      1.00      1.00      1.00      1.00      1.50      1.31      1.50      1.50      6.33      6.33        /         /         /         /         /         /         /         /         /         /         / 
 │     └─specs                                        1.00      1.00      1.00      1.00      1.00      1.50      1.31      1.50      1.50      6.33      6.33        /         /         /         /         /         /         /         /         /         /         / 
 │        ├─arm_v9_cortex_v3                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      6.50      6.50        /         /         /         /         /         /         /         /         /         /         / 
 │        ├─arm_v9_cortex_x4                          1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.50      1.50      6.50      6.50        /         /         /         /         /         /         /         /         /         /         / 
 │        └─arm_v9_cortex_x925                        1.00      1.00      1.00      1.00      1.00      1.50      1.00      1.50      1.50      6.00      6.00        /         /         /         /         /         /         /         /         /         /         / 
 └─x86                                                0.42      0.42      1.00      1.01      1.40      1.30      1.76      2.09      2.60      5.14      6.76        /         /         /         /      32.35     52.74        /         /         /         /      80.16
    ├─amd                                             0.44      0.44      1.00      1.01      1.81      1.18      1.02      2.19      2.61      4.85      6.94        /         /         /         /      32.91    173.48        /         /         /         /      94.73
    │  ├─2017_zen1                                    0.46      0.48      1.00      1.04      1.57      1.14      1.14      2.22      3.51      4.46      5.06        /         /         /         /      32.94    173.63        /         /         /         /      94.81
    │  │  ├─analysis_uops_info_zen1+                  0.33      0.33      1.00      1.00      2.33      1.33      0.67      2.11      3.33      4.33      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  │  └─benchmark_ryzen_1700x                     0.64      0.69      1.00      1.08      1.06      0.97      1.97        /         /       4.58      3.83        /         /         /         /      34.68    182.82        /         /         /         /      99.82
    │  ├─2020_zen3                                    0.33      0.33      1.00      1.00      1.97      1.01      0.76      2.01      2.45      4.42      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  │  ├─analysis_agner_fog_r7_5800x               0.33      0.33      1.00      1.00      1.67        /       1.00      2.33      2.00      4.50      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  │  └─analysis_uops_info_zen3                   0.33      0.33      1.00      1.00      2.33      1.00      0.58      1.73      3.00      4.33      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  ├─2022_zen4                                    0.33      0.33      1.00      1.00      1.28      1.02      0.83      1.63      2.00      4.33      6.89        /         /         /         /         /         /         /         /         /         /         / 
    │  │  ├─analysis_agner_fog_r9_7900x               0.33      0.33      1.00      1.00      1.33        /       1.00      2.00      2.00      4.33      7.00        /         /         /         /         /         /         /         /         /         /         / 
    │  │  ├─analysis_uops_info_zen4                   0.33      0.33      1.00      1.00      2.33      1.00      0.58      1.63      3.00      4.33      7.00        /         /         /         /         /         /         /         /         /         /         / 
    │  │  └─specs_amd                                 0.33      0.33      1.00      1.00      0.67      1.00      1.00      1.33      1.33      4.33      6.67        /         /         /         /         /         /         /         /         /         /         / 
    │  └─2024_zen5                                    0.71      0.71      1.00      1.00      2.72      1.66      1.50      3.17      2.72      6.50     10.00        /         /         /         /         /         /         /         /         /         /         / 
    │     ├─analysis_agner_fog_r7_9800x3d             1.00      1.00      1.00      1.00      3.00        /       1.50      3.50      3.00      6.50     10.00        /         /         /         /         /         /         /         /         /         /         / 
    │     └─specs_amd                                 0.50      0.50      1.00      1.00        /       1.50      1.50        /         /       6.50     10.00        /         /         /         /         /         /         /         /         /         /         / 
    └─intel                                           0.40      0.40      1.00      1.01      1.09      1.43      3.02      1.99      2.58      5.45      6.59        /         /         /         /      31.80     16.03        /         /         /         /      67.83
       ├─2017_coffee_lake_gen_8                       0.25      0.25      1.00      1.00      0.74      1.00      2.00      1.41      1.62      3.56      4.29        /         /         /         /         /         /         /         /         /         /         / 
       │  ├─analysis_agner_fog_coffee_lake            0.25      0.25      1.00      1.00        /       1.00      2.00      1.50      1.50      3.37      3.87        /         /         /         /         /         /         /         /         /         /         / 
       │  └─analysis_uops_info_coffee_lake            0.25      0.25      1.00      1.00      0.75      1.00      2.00      1.32      1.75      3.75      4.75        /         /         /         /         /         /         /         /         /         /         / 
       ├─2019_sunny_cove_gen_10                       0.25      0.25      1.00      1.00      0.66      0.98      2.00      1.38      1.66      3.62      4.44        /         /         /         /         /         /         /         /         /         /         / 
       │  ├─analysis_agner_fog_ice_lake               0.25      0.25      1.00      1.00      0.50        /       2.00      1.50      1.50      3.37      3.87        /         /         /         /         /         /         /         /         /         /         / 
       │  ├─analysis_uops_info_ice_lake               0.25      0.25      1.00      1.00      0.75      1.00      2.00      1.32      1.75      3.75      4.75        /         /         /         /         /         /         /         /         /         /         / 
       │  └─analysis_uops_info_tiger_lake             0.25      0.25      1.00      1.00      0.75      1.00      2.00      1.32      1.75      3.75      4.75        /         /         /         /         /         /         /         /         /         /         / 
       ├─2021_golden_cove_gen_12                      0.64      0.64      1.00      1.07      1.39      1.53      3.93      2.54      3.46      7.61      8.07        /         /         /         /      40.46     20.40        /         /         /         /      86.31
       │  ├─analysis_uops_info_alder_lake_p           0.41      0.41      1.00      1.00      1.22      1.63      3.27      2.16      2.86      6.12      7.76        /         /         /         /         /         /         /         /         /         /         / 
       │  ├─benchmark_core_i7_1265u                   1.28      1.25      1.00      1.21      1.47      1.10      4.65        /         /      10.27      7.54        /         /         /         /      48.46     24.43        /         /         /         /     103.37
       │  └─specs_intel                               0.50      0.50      1.00      1.00      1.50      2.00      4.00      2.50      3.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
       ├─2022_raptor_cove_gen_13_14                   0.50      0.50      1.00      1.00      1.50      2.00      4.00      2.50      3.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
       │  └─specs_intel                               0.50      0.50      1.00      1.00      1.50      2.00      4.00      2.50      3.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
       └─2023_redwood_cove_ultra_1                    0.50      0.50      1.00      1.00      1.50      2.00      4.00      2.50      3.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
          └─specs_intel                               0.50      0.50      1.00      1.00      1.50      2.00      4.00      2.50      3.50      7.00      9.00        /         /         /         /         /         /         /         /         /         /         / 
```

# 5. Known limitations

- currently any non-Python-built-in math operations are not counted (e.g. `numpy`)
- not all Python built-in math operations are counted (e.g. `log`, `log10`, `exp`, `exp10`)
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