# counted-float

`counted-float` counts floating-point operations (FLOPs) of numerical
algorithms implemented in plain Python, optionally weighted by their relative
cost of execution, and can run benchmarks to estimate those relative costs on
your own hardware.

The target application area is evaluation of research prototypes of numerical
algorithms, where (weighted) FLOP counting can be useful for estimating total
computational cost in cases where benchmarking a compiled version (C, Rust,
...) is not feasible or desirable.

## Installation

Use your favorite package manager such as `uv` or `pip`:

```
pip install counted-float           # install without numba optional dependency
pip install counted-float[numba]    # install with numba optional dependency
```

Numba is optional due to its relatively large size (40-50MB, including
llvmlite), but without it, benchmarks will not be reliable (they will still
run, but not in jit-compiled form).
