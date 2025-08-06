![shields.io](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![genbadge](https://bertpl.github.io/counted-float/badges/tests.svg)
![genbadge](https://bertpl.github.io/counted-float/badges/coverage.svg)

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

**NOTE:** This functionality is planned for release 0.2.0.

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