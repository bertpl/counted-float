<!--START_SECTION:images-->
![shields.io-python-versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![genbadge-test-count](https://bertpl.github.io/counted-float/version_artifacts/v0.9.2/badge-test-count.svg)
![genbadge-test-coverage](https://bertpl.github.io/counted-float/version_artifacts/v0.9.2/badge-coverage.svg)
![counted_float logo](https://bertpl.github.io/counted-float/version_artifacts/v0.9.2/splash.webp)
<!--END_SECTION:images-->

# counted-float

This Python package provides functionality for...
- **counting floating point operations** (FLOPs) of numerical algorithms implemented in plain Python, optionally weighted by their relative cost of execution
- **running benchmarks** to estimate the relative cost of executing various floating-point operations (requires `numba` optional dependency for achieving accurate results)

The target application area is evaluation of research prototypes of numerical algorithms where (weighted) flop counting can be 
useful for estimating total computational cost, in cases where benchmarking a compiled version (C, Rust, ...) is not 
feasible or desirable.

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
that require counting (`sqrt`, `log2`, `pow`) are also instrumented.

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

```
>>> from counted_float.config import get_flop_weights
>>> get_flop_weights().show()

{
    FlopType.ABS        [abs(x)]        :    1
    FlopType.MINUS      [-x]            :    1
    FlopType.EQUALS     [x==y]          :    1
    FlopType.GTE        [x>=y]          :    1
    FlopType.LTE        [x<=y]          :    1
    FlopType.CMP_ZERO   [x>=0]          :    1
    FlopType.RND        [round(x)]      :    1
    FlopType.ADD        [x+y]           :    1
    FlopType.SUB        [x-y]           :    1
    FlopType.MUL        [x*y]           :    1
    FlopType.DIV        [x/y]           :    3
    FlopType.SQRT       [sqrt(x)]       :    3
    FlopType.POW2       [2^x]           :   12
    FlopType.LOG2       [log2(x)]       :   14
    FlopType.POW        [x^y]           :   33
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
total_cost = flop_counts.total_weighted_cost()  # 1 + 33 + 14 = 48
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

Built-in empirical, theoretical and consensus built-in flop weights can be inspected using the following functions:

```python
from counted_float.config import get_default_empirical_flop_weights, get_default_theoretical_flop_weights, get_default_consensus_flop_weights

>>> get_default_empirical_flop_weights(rounded=False).show()

{
    FlopType.ABS        [abs(x)]        :   0.90744
    FlopType.MINUS      [-x]            :   0.80068
    FlopType.EQUALS     [x==y]          :   0.93532
    FlopType.GTE        [x>=y]          :   0.94684
    FlopType.LTE        [x<=y]          :   0.93101
    FlopType.CMP_ZERO   [x>=0]          :   0.82204
    FlopType.RND        [round(x)]      :   0.96944
    FlopType.ADD        [x+y]           :   0.89296
    FlopType.SUB        [x-y]           :   1.14383
    FlopType.MUL        [x*y]           :   1.04677
    FlopType.DIV        [x/y]           :   3.10940
    FlopType.SQRT       [sqrt(x)]       :   2.56566
    FlopType.POW2       [2^x]           :  10.80030
    FlopType.LOG2       [log2(x)]       :  16.32770
    FlopType.POW        [x^y]           :  40.50382
}
```

The default weights that are configured in the package are the integer-rounded `consensus` weights.

### 2.5.2. Custom-aggregated flop weights

We can retrieve built-in flop weights in a more fine-grained manner, by custom filtering and the aggregating them with
the geometric mean.

```python
from counted_float.config import get_builtin_flop_weights

>>> get_builtin_flop_weights(key_filter="intel").show()

{
    FlopType.ABS        [abs(x)]        :   0.56708
    FlopType.MINUS      [-x]            :   0.44910
    FlopType.EQUALS     [x==y]          :   0.89744
    FlopType.GTE        [x>=y]          :   0.89744
    FlopType.LTE        [x<=y]          :   0.89744
    FlopType.CMP_ZERO   [x>=0]          :   0.84762
    FlopType.RND        [round(x)]      :   2.63592
    FlopType.ADD        [x+y]           :   0.86616
    FlopType.SUB        [x-y]           :   1.10411
    FlopType.MUL        [x*y]           :   1.16515
    FlopType.DIV        [x/y]           :   4.55230
    FlopType.SQRT       [sqrt(x)]       :   4.37234
    FlopType.POW2       [2^x]           :  14.78792
    FlopType.LOG2       [log2(x)]       :  20.51270
    FlopType.POW        [x^y]           :  40.16390
}
```

The 3 built-in *default* flop weights are simply presets for the `key_filter` argument:  
* `get_default_empirical_flop_weights()` --> `get_built_in_flop_weights(key_filter="benchmarks")`
* `get_default_theoretical_flop_weights()` --> `get_built_in_flop_weights(key_filter="specs")`
* `get_default_consensus_flop_weights()` --> `get_built_in_flop_weights(key_filter="")`

# 3. Benchmarking

If the package is installed with the optional `numba` dependency, it provides the ability to micro-benchmark 
floating point operations as follows:

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

Running FLOPS benchmarks using counted-float 0.9.2 ...

baseline                           : wwwwwwwwww....................   ( 187.03 ns =   759 cpu cycles) ±  0.6%  /  1000 iterations
FlopType.ABS        [abs(x)]       : wwwwwwwwww....................   ( 303.31 ns = 1.23K cpu cycles) ±  1.7%  /  1000 iterations
FlopType.CMP_ZERO   [x>=0]         : wwwwwwwwww....................   ( 302.19 ns = 1.23K cpu cycles) ±  3.0%  /  1000 iterations
FlopType.RND        [round(x)]     : wwwwwwwwww....................   ( 305.95 ns = 1.24K cpu cycles) ±  4.8%  /  1000 iterations
FlopType.MINUS      [-x]           : wwwwwwwwww....................   ( 306.31 ns = 1.24K cpu cycles) ±  2.6%  /  1000 iterations
FlopType.EQUALS     [x==y]         : wwwwwwwwww....................   ( 320.59 ns = 1.30K cpu cycles) ±  3.9%  /  1000 iterations
FlopType.GTE        [x>=y]         : wwwwwwwwww....................   ( 331.51 ns = 1.34K cpu cycles) ±  2.9%  /  1000 iterations
FlopType.LTE        [x<=y]         : wwwwwwwwww....................   ( 333.81 ns = 1.35K cpu cycles) ±  1.0%  /  1000 iterations
FlopType.ADD        [x+y]          : wwwwwwwwww....................   ( 315.84 ns = 1.28K cpu cycles) ±  3.2%  /  1000 iterations
FlopType.SUB        [x-y]          : wwwwwwwwww....................   ( 335.49 ns = 1.36K cpu cycles) ±  3.8%  /  1000 iterations
FlopType.MUL        [x*y]          : wwwwwwwwww....................   ( 325.65 ns = 1.32K cpu cycles) ±  3.0%  /  1000 iterations
FlopType.SQRT       [sqrt(x)]      : wwwwwwwwww....................   ( 443.30 ns = 1.80K cpu cycles) ±  2.6%  /  1000 iterations
FlopType.DIV        [x/y]          : wwwwwwwwww....................   ( 491.51 ns = 1.99K cpu cycles) ±  1.1%  /  1000 iterations
FlopType.POW2       [2^x]          : wwwwwwwwww....................   (   1.79 µs = 7.28K cpu cycles) ±  0.3%  /  1000 iterations
FlopType.LOG2       [log2(x)]      : wwwwwwwwww....................   (   2.17 µs = 8.80K cpu cycles) ±  0.8%  /  1000 iterations
FlopType.POW        [x^y]          : wwwwwwwwww....................   (   6.32 µs = 25.6K cpu cycles) ±  0.7%  /  1000 iterations

>>> results.flop_weights.show() 

{
    FlopType.ABS        [abs(x)]        :   0.84769
    FlopType.MINUS      [-x]            :   0.86954
    FlopType.EQUALS     [x==y]          :   0.97369
    FlopType.GTE        [x>=y]          :   1.05327
    FlopType.LTE        [x<=y]          :   1.07007
    FlopType.CMP_ZERO   [x>=0]          :   0.83957
    FlopType.RND        [round(x)]      :   0.86695
    FlopType.ADD        [x+y]           :   0.93905
    FlopType.SUB        [x-y]           :   1.08227
    FlopType.MUL        [x*y]           :   1.01055
    FlopType.DIV        [x/y]           :   2.21970
    FlopType.SQRT       [sqrt(x)]       :   1.86822
    FlopType.POW2       [2^x]           :  11.72183
    FlopType.LOG2       [log2(x)]       :  14.45542
    FlopType.POW        [x^y]           :  44.68266
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

## 4.1 Running benchmarks

```
counted_float benchmark
```
after which the results will be shown as .json.

## 4.2. Show built-in data

```
[~] counted_float show-data
                                           MINUS       ABS  CMP_ZERO       LTE    EQUALS       GTE       ADD       SUB       MUL       RND      SQRT       DIV      POW2      LOG2       POW
ALL                                         0.59      0.63      0.74      0.90      0.90      0.90      0.92      1.05      1.15      1.25      3.55      3.57     12.33     14.68     34.01
 ├─benchmarks                               0.80      0.91      0.82      0.93      0.94      0.95      0.89      1.14      1.05      0.97      2.57      3.11     10.80     16.33     40.50
 │  ├─arm                                   0.99      0.79      0.88      1.00      1.01      1.04      0.99      1.00      1.00      0.88      1.83      2.17     11.46     14.24     45.98
 │  │  └─apple                              0.99      0.79      0.88      1.00      1.01      1.04      0.99      1.00      1.00      0.88      1.83      2.17     11.46     14.24     45.98
 │  │     └─m3_max_macbook_pro_16           0.99      0.79      0.88      1.00      1.01      1.04      0.99      1.00      1.00      0.88      1.83      2.17     11.46     14.24     45.98
 │  └─x86                                   0.65      1.04      0.77      0.87      0.87      0.87      0.81      1.31      1.09      1.07      3.59      4.46     10.18     18.72     35.68
 │     └─intel                              0.65      1.04      0.77      0.87      0.87      0.87      0.81      1.31      1.09      1.07      3.59      4.46     10.18     18.72     35.68
 │        ├─gen12_i7_1265u                  1.06      1.08      1.26      1.24      1.24      1.24      0.85      1.02      0.93      3.94      6.38      8.69     20.67     40.99     87.44
 │        └─gen7_i5_7200u                   0.40      0.99      0.47      0.60      0.60      0.60      0.77      1.68      1.29      0.29      2.03      2.29      5.01      8.55     14.56
 └─specs                                    0.43      0.43      0.67      0.86      0.86      0.86      0.96      0.96      1.27      1.61      4.92      4.09     14.08     13.20     28.56
    ├─arm                                   0.82      0.82      0.65      0.65      0.65      0.65      1.03      1.03      1.45      1.35      5.92      5.53        /         /         / 
    │  ├─arm_v7a_cortex_a9                  0.32      0.32      0.32      0.32      0.32      0.32      1.28      1.28      1.92      1.28     10.22      7.99        /         /         / 
    │  ├─arm_v8_cortex_a55                  1.41      1.41      0.35      0.35      0.35      0.35      1.41      1.41      1.41      1.41      7.78      7.78        /         /         / 
    │  ├─arm_v8_cortex_a76                  0.90      0.90      0.90      0.90      0.90      0.90      0.90      0.90      1.36      1.36      4.93      4.63        /         /         / 
    │  ├─arm_v9_cortex_x1                   0.90      0.90      0.90      0.90      0.90      0.90      0.90      0.90      1.36      1.36      4.78      4.63        /         /         / 
    │  ├─arm_v9_cortex_x2                   0.90      0.90      0.90      0.90      0.90      0.90      0.90      0.90      1.36      1.36      4.78      4.63        /         /         / 
    │  └─arm_v9_cortex_x3                   0.90      0.90      0.90      0.90      0.90      0.90      0.90      0.90      1.36      1.36      4.78      4.63        /         /         / 
    └─x86                                   0.23      0.23      0.70      1.14      1.14      1.14      0.89      0.89      1.11      1.92      4.09      3.02     12.96     12.15     26.29
       ├─amd                                0.17      0.17        /       1.45      1.45      1.45      0.88      0.88      0.88      0.59      3.26      2.04      7.89      6.93     15.71
       │  ├─zen3_r7_5800x                   0.14      0.14        /       1.49      1.49      1.49      0.88      0.88      0.88      0.54      3.38      2.03      7.40      6.62     14.90
       │  ├─zen4_r9_7900x                   0.13      0.13        /       1.40      1.40      1.40      0.89      0.89      0.89      0.64      3.19      1.91      6.99      6.25     14.13
       │  └─zen5_r7_9800x3d                 0.29      0.29        /       1.47      1.47      1.47      0.88      0.88      0.88      0.59      3.23      2.20      9.51      8.03     18.42
       └─intel                              0.30      0.30      0.90      0.90      0.90      0.90      0.90      0.90      1.39      6.28      5.12      4.47     21.27     21.31     43.97
          ├─gen09_coffee_lake               0.29      0.29      0.88      0.88      0.88      0.88      0.88      0.88      1.47      6.16      5.03      4.39     21.16     20.74     43.37
          ├─gen10_cannon_lake               0.29      0.29      0.88      0.88      0.88      0.88      0.88      0.88      1.47      6.16      5.03      4.39     21.16     20.74     43.37
          └─gen11_tiger_lake                0.31      0.31      0.93      0.93      0.93      0.93      0.93      0.93      1.24      6.51      5.32      4.64     21.49     22.48     45.21
```

# 5. Known limitations

- currently any non-Python-built-in math operations are not counted (e.g. `numpy`)
- not all Python built-in math operations are counted (e.g. `log`, `log10`, `exp`, `exp10`)
- flop weights should be taken with a grain of salt and should only provide relative ballpark estimates w.r.t computational complexity.  Production implementations in a compiled language could have vastly differing performance depending on cpu cache sizes, branch prediction misses, compiler optimizations using vector operations (AVX etc...), etc...