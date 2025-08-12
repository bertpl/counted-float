<!--START_SECTION:badges-->
![shields.io](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![genbadge](https://bertpl.github.io/counted-float/badges/v0.8.2/tests.svg)
![genbadge](https://bertpl.github.io/counted-float/badges/v0.8.2/coverage.svg)
<!--END_SECTION:badges-->

# counted-float

This Python package provides functionality for counting the number of floating point operations (FLOPs) of numerical
algorithms implemented in plain Python.

The target application area are research prototypes of numerical algorithms where (weighted) flop counting can be 
useful for estimating total computational cost, in cases where benchmarking a compiled version (C, Rust, ...) is not 
feasible or desirable.

The package contains two components:
 - `counting`: provides a CountedFloat class & flop counting context managers to count flops of code blocks.
 - `benchmarking`: (optional) provides functionality to micro-benchmark floating point operations to get an empirical
   ballpark estimate of the relative cost of different operations on the target hardware.

# 1. Installation



Use you favorite package manager such as `uv` or `pip`:

```
pip install counted-float                  # install without benchmarking optional dependencies
pip install counted-float[benchmarking]    # install with benchmarking optional dependencies
```
Benchmarking dependencies are optional due to the large size of the numba (+llvmlite) package, which is used for
micro-benchmarking, which relies on jit-compiled code to get more accurate estimates with less Python overhead. 

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
    _ = cf1 + cf2   # will be executed but bot counted
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
        _ = cf1 + cf2   # will be executed but bot counted
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
    FlopType.SQRT       [sqrt(x)]       :    4
    FlopType.POW2       [2^x]           :   12
    FlopType.LOG2       [log2(x)]       :   15
    FlopType.POW        [x^y]           :   32
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
total_cost = flop_counts.total_weighted_cost()  # 1 + 32 + 15 = 48
```
Note that the `total_weighted_cost` method will use the default flop weights as returned by `get_flop_weights()`.  This can be
overridden by either configure different flop weights (see next section) or by setting the `weights` argument of the `total_weighted_cost()` method.


## 2.4. Configuring FLOP weights

We showed earlier that the `get_flop_weights()` function returns the default FLOP weights.  We can change this by
using the `set_flop_weights()` function, which takes a `FlopWeights` object as an argument.  This way we can configure
flop weights that might be obtained using benchmarks run on the target hardware (see later sections).

```python
from counted_float.config import set_flop_weights
from counted_float import FlopWeights

set_flop_weights(weights=FlopWeights(...))  # insert own weights here
```
## 2.5. Inspecting built-in data

Built-in empirical, theoretical and consensus built-in flop weights can be inspected using the following functions:

```python
from counted_float.config import get_default_empirical_flop_weights, get_default_theoretical_flop_weights, get_default_consensus_flop_weights

>>> get_default_empirical_flop_weights(rounded=False).show()

{
    FlopType.ABS        [abs(x)]        :   0.94863
    FlopType.MINUS      [-x]            :   0.74700
    FlopType.EQUALS     [x==y]          :   0.91142
    FlopType.GTE        [x>=y]          :   0.91889
    FlopType.LTE        [x<=y]          :   0.90862
    FlopType.CMP_ZERO   [x>=0]          :   0.80503
    FlopType.RND        [round(x)]      :   1.00080
    FlopType.ADD        [x+y]           :   0.86304
    FlopType.SUB        [x-y]           :   1.19673
    FlopType.MUL        [x*y]           :   1.06232
    FlopType.DIV        [x/y]           :   3.50765
    FlopType.SQRT       [sqrt(x)]       :   2.87080
    FlopType.POW2       [2^x]           :  10.58784
    FlopType.LOG2       [log2(x)]       :  17.08929
    FlopType.POW        [x^y]           :  38.82827
}
```

These 3 types of built-in weights are defined as follows:
* `empirical`: geo-mean of the flop weights corresponding to the built-in **benchmarking** results
* `theoretical`: geo-mean of the flop weights corresponding to the built-in **specification analyses** (FPU instruction latencies)
* `consensus`: geo-mean of the `empirical` and `theoretical` flop weights

The default weights that are configured in the package are the integer-rounded `consensus` weights.

# 3. Benchmarking

If the package is installed with the optional `benchmarking` dependencies, it provides
the ability to micro-benchmark floating point operations as follows:

```
>>> from counted_float.benchmarking import run_flops_benchmark
>>> results = run_flops_benchmark()

baseline                           : wwwwwwwwww....................    186.43 ns ±    0.82 ns / operation
FlopType.ABS        [abs(x)]       : wwwwwwwwww....................    300.85 ns ±    5.26 ns / operation
FlopType.CMP_ZERO   [x>=0]         : wwwwwwwwww....................    307.79 ns ±    6.65 ns / operation
FlopType.RND        [round(x)]     : wwwwwwwwww....................    307.62 ns ±    5.12 ns / operation
FlopType.MINUS      [-x]           : wwwwwwwwww....................    302.88 ns ±    4.51 ns / operation
FlopType.EQUALS     [x==y]         : wwwwwwwwww....................    328.41 ns ±    5.73 ns / operation
FlopType.GTE        [x>=y]         : wwwwwwwwww....................    326.37 ns ±    5.07 ns / operation
FlopType.LTE        [x<=y]         : wwwwwwwwww....................    322.10 ns ±    4.74 ns / operation
FlopType.ADD        [x+y]          : wwwwwwwwww....................    317.28 ns ±    9.27 ns / operation
FlopType.SUB        [x-y]          : wwwwwwwwww....................    320.05 ns ±    6.38 ns / operation
FlopType.MUL        [x*y]          : wwwwwwwwww....................    325.44 ns ±    4.00 ns / operation
FlopType.SQRT       [sqrt(x)]      : wwwwwwwwww....................    452.21 ns ±    4.32 ns / operation
FlopType.DIV        [x/y]          : wwwwwwwwww....................    482.68 ns ±    0.93 ns / operation
FlopType.POW2       [2^x]          : wwwwwwwwww....................      1.77 µs ±    0.00 µs / operation
FlopType.LOG2       [log2(x)]      : wwwwwwwwww....................      2.15 µs ±    0.01 µs / operation
FlopType.POW        [x^y]          : wwwwwwwwww....................      6.55 µs ±    0.01 µs / operation

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

# 4. Known limitations

- currently any non-Python-built-in math operations are not counted (e.g. `numpy`)
- not all Python built-in math operations are counted (e.g. `log`, `log10`, `exp`, `exp10`)
- flop weights should be taken with a grain of salt and should only provide relative ballpark estimates w.r.t computational complexity.  Production implementations in a compiled language could have vastly differing performance depending on cpu cache sizes, branch prediction misses, compiler optimizations using vector operations (AVX etc...), etc...