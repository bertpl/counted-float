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

baseline                      : wwwwwwwwww....................    218.71 ns ±    1.47 ns / operation
c=abs(a)                      : wwwwwwwwww....................    331.25 ns ±    5.64 ns / operation
c=(a>=0)                      : wwwwwwwwww....................    337.88 ns ±    8.92 ns / operation
c=ceil(a)                     : wwwwwwwwww....................    329.89 ns ±    4.00 ns / operation
c=-a                          : wwwwwwwwww....................    333.21 ns ±    4.99 ns / operation
c=(a==b)                      : wwwwwwwwww....................    354.99 ns ±    4.85 ns / operation
c=(a>=b)                      : wwwwwwwwww....................    352.01 ns ±    6.27 ns / operation
c=(a<=b)                      : wwwwwwwwww....................    351.94 ns ±    6.03 ns / operation
c=a+b                         : wwwwwwwwww....................    346.22 ns ±    4.61 ns / operation
c=a-b                         : wwwwwwwwww....................    350.77 ns ±    8.45 ns / operation
c=a*b                         : wwwwwwwwww....................    345.23 ns ±    5.57 ns / operation
c=sqrt(a)                     : wwwwwwwwww....................    477.92 ns ±    2.78 ns / operation
c=a/b                         : wwwwwwwwww....................    513.39 ns ±    2.96 ns / operation
c=2**a                        : wwwwwwwwww....................      1.80 µs ±    0.00 µs / operation
c=log2(a)                     : wwwwwwwwww....................      2.17 µs ±    0.01 µs / operation
c=a^b                         : wwwwwwwwww....................      6.60 µs ±    0.01 µs / operation

>>> result.flop_weights.print() 

{
    "weights": {
        "abs(x)": 0.8621431123617258,
        "-x": 0.877162001570882,
        "x==y": 1.0440190272083842,
        "x>=y": 1.0211908077124046,
        "x<=y": 1.0206239758063622,
        "x>=0": 0.9129479117929392,
        "round(x)": 0.8517231697599011,
        "x+y": 0.9768284351219878,
        "x-y": 1.0116551232199238,
        "x*y": 0.9692611546908555,
        "x/y": 2.2574503148692138,
        "sqrt(x)": 1.9857266998711156,
        "2^x": 12.127727096594114,
        "log2(x)": 14.932183767553829,
        "x^y": 48.866160190275906
    }
}
```

# 4. Known limitations

- currently any non-Python-built-in math operations are not counted (e.g. `numpy`)
- not all Python built-in math operations are counted (e.g. `log`, `log10`, `exp`, `exp10`)
- flop weights should be taken with a grain of salt and should only provide relative ballpark estimates w.r.t computational complexity.  Production implementations in a compiled language could have vastly differing performance depending on cpu cache sizes, branch prediction misses, compiler optimizations using vector operations (AVX etc...), etc...