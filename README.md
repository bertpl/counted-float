<!--START_SECTION:images-->
![shields.io-python-versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![genbadge-test-count](https://bertpl.github.io/counted-float/version_artifacts/v0.9.1/badge-test-count.svg)
![genbadge-test-coverage](https://bertpl.github.io/counted-float/version_artifacts/v0.9.1/badge-coverage.svg)
![counted_float logo](https://bertpl.github.io/counted-float/version_artifacts/v0.9.1/splash.webp)
<!--END_SECTION:images-->

# counted-float

This Python package provides functionality for counting the number of floating point operations (FLOPs) of numerical
algorithms implemented in plain Python.

The target application area are research prototypes of numerical algorithms where (weighted) flop counting can be 
useful for estimating total computational cost, in cases where benchmarking a compiled version (C, Rust, ...) is not 
feasible or desirable.

The package contains two components:
 - `counting`: provides a CountedFloat class & flop counting context managers to count flops of code blocks.
 - `benchmarking`: provides functionality to micro-benchmark floating point operations to get an empirical
   ballpark estimate of the relative cost of different operations on the target hardware.  Requires 'numba' optional dependency for accurate results.

# 1. Installation



Use you favorite package manager such as `uv` or `pip`:

```
pip install counted-float           # install without numba optional dependency
pip install counted-float[numba]    # install with numba optional dependency
```
Numba is optional due to its relatively large size (40-50MB, including llvmlite), but without it, benchmarks will
not be reliable (but will still run, but not in jit-compiled form).

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

## 3.1. General

If the package is installed with the optional `numba` dependency, it provides
the ability to micro-benchmark floating point operations as follows:

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

Running FLOPS benchmarks using counted-float 0.9.0 ...

baseline                           : wwwwwwwwww....................    187.97 ns ±    0.52 ns / 1000 flops
FlopType.ABS        [abs(x)]       : wwwwwwwwww....................    307.23 ns ±    8.37 ns / 1000 flops
FlopType.CMP_ZERO   [x>=0]         : wwwwwwwwww....................    301.36 ns ±    7.22 ns / 1000 flops
FlopType.RND        [round(x)]     : wwwwwwwwww....................    302.96 ns ±    8.39 ns / 1000 flops
FlopType.MINUS      [-x]           : wwwwwwwwww....................    304.00 ns ±    7.99 ns / 1000 flops
FlopType.EQUALS     [x==y]         : wwwwwwwwww....................    319.64 ns ±    6.71 ns / 1000 flops
FlopType.GTE        [x>=y]         : wwwwwwwwww....................    325.35 ns ±    9.26 ns / 1000 flops
FlopType.LTE        [x<=y]         : wwwwwwwwww....................    323.17 ns ±   11.45 ns / 1000 flops
FlopType.ADD        [x+y]          : wwwwwwwwww....................    316.96 ns ±   11.11 ns / 1000 flops
FlopType.SUB        [x-y]          : wwwwwwwwww....................    318.59 ns ±    9.36 ns / 1000 flops
FlopType.MUL        [x*y]          : wwwwwwwwww....................    318.11 ns ±    7.16 ns / 1000 flops
FlopType.SQRT       [sqrt(x)]      : wwwwwwwwww....................    449.06 ns ±    2.42 ns / 1000 flops
FlopType.DIV        [x/y]          : wwwwwwwwww....................    483.70 ns ±    2.00 ns / 1000 flops
FlopType.POW2       [2^x]          : wwwwwwwwww....................      1.77 µs ±    0.00 µs / 1000 flops
FlopType.LOG2       [log2(x)]      : wwwwwwwwww....................      2.13 µs ±    0.01 µs / 1000 flops
FlopType.POW        [x^y]          : wwwwwwwwww....................      6.53 µs ±    0.00 µs / 1000 flops


>>> results.flop_weights.show() 

{
    FlopType.ABS        [abs(x)]        :   0.83953
    FlopType.MINUS      [-x]            :   0.85441
    FlopType.EQUALS     [x==y]          :   1.04173
    FlopType.GTE        [x>=y]          :   1.02677
    FlopType.LTE        [x<=y]          :   0.99542
    FlopType.CMP_ZERO   [x>=0]          :   0.89041
    FlopType.RND        [round(x)]      :   0.88915
    FlopType.ADD        [x+y]           :   0.96007
    FlopType.SUB        [x-y]           :   0.98034
    FlopType.MUL        [x*y]           :   1.01992
    FlopType.DIV        [x/y]           :   2.17358
    FlopType.SQRT       [sqrt(x)]       :   1.95006
    FlopType.POW2       [2^x]           :  11.65331
    FlopType.LOG2       [log2(x)]       :  14.38278
    FlopType.POW        [x^y]           :  46.72479
}
```

## 3.2. Using `uv`

There's a lower-threshold way of running benchmarks if you have `uv` installed.  Simply install the package including `numba`.

```
uv tool install git+https://github.com/bertpl/counted-float@main[numba]         # latest official release
uv tool install git+https://github.com/bertpl/counted-float@develop[numba]      # or latest develop version
```
After which you can run the `run_flops_benchmarks` command from the command line:
```
run_flops_benchmark
```
Final results will be shown as json.


# 4. Known limitations

- currently any non-Python-built-in math operations are not counted (e.g. `numpy`)
- not all Python built-in math operations are counted (e.g. `log`, `log10`, `exp`, `exp10`)
- flop weights should be taken with a grain of salt and should only provide relative ballpark estimates w.r.t computational complexity.  Production implementations in a compiled language could have vastly differing performance depending on cpu cache sizes, branch prediction misses, compiler optimizations using vector operations (AVX etc...), etc...