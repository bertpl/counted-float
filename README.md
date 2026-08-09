<!-- badges below refreshed at release v2.4.0 -->
[![CI](https://img.shields.io/github/actions/workflow/status/bertpl/counted-float/push_to_main.yml?branch=main&label=CI)](https://github.com/bertpl/counted-float/actions/workflows/push_to_main.yml)
[![Coverage](https://img.shields.io/badge/coverage-100.00%25-brightgreen)](https://github.com/bertpl/counted-float/actions/workflows/push_to_main.yml)
[![Tests](https://img.shields.io/badge/tests-2425-blue)](https://github.com/bertpl/counted-float/actions/workflows/push_to_main.yml)
[![Mutation](https://img.shields.io/badge/mutmut-84%25-brightgreen)](https://pypi.org/project/mutmut/)
[![Docs](https://img.shields.io/readthedocs/counted-float)](https://counted-float.readthedocs.io/)
[![PyPI](https://img.shields.io/pypi/v/counted-float.svg)](https://pypi.org/project/counted-float/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21780137.svg)](https://doi.org/10.5281/zenodo.21780137)
[![Python](https://img.shields.io/pypi/pyversions/counted-float.svg)](https://pypi.org/project/counted-float/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/bertpl/counted-float/blob/main/LICENSE)
[![code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230)](https://github.com/astral-sh/ruff)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/bertpl/counted-float/badge)](https://scorecard.dev/viewer/?uri=github.com/bertpl/counted-float)

![counted_float logo](images/splash_with_version.webp)

# counted-float

This Python package provides functionality for...

- **counting floating point operations** (FLOPs) of numerical algorithms implemented in plain Python, optionally weighted by their relative cost of execution
- **running benchmarks** to estimate the relative cost of executing various floating-point operations (requires the `benchmarking` optional dependency)

Flop weights are computed using a highly curated dataset spanning a wide range of modern CPUs:

<!-- BEGIN generated: source-counts -->
- 21 benchmarks, 16 spec sheets, 12 third party measurements (Agner Fog, uops.info)
<!-- END generated: source-counts -->
- covering x86 (Intel, AMD) and ARM (Apple, AWS, Azure) architectures

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/flop_weights_dark.svg">
    <img alt="Built-in flop weights, relative to ADD, per architecture" src="docs/images/flop_weights_light.svg">
  </picture>
</div>

The target application area is evaluation of research prototypes of numerical algorithms where (weighted) flop counting can be
useful for estimating total computational cost, in cases where benchmarking a compiled version (C, Rust, ...) is not
feasible or desirable.

**Full documentation: [counted-float.readthedocs.io](https://counted-float.readthedocs.io/)**

## Installation

Use your favorite package manager such as `uv` or `pip`. What you install decides which of
the three capabilities you get:

```
pip install counted-float                  # counting
pip install counted-float[benchmarking]    # + measure this machine's flop costs
pip install counted-float[cli]             # + the counted_float command
```

**Counting** is the base install and needs nothing else. Building `CountedFloat`
values, counting contexts, the built-in flop weights, reading benchmark results
shipped with the package, and evaluating what counting costs you on your own
workload all work here. It is about 17 MB installed.

**Benchmarking** measures *your machine* — running the flop benchmark suite to
derive weights for the hardware you are on, rather than using the shipped
consensus ones. It needs compiled probes (numba) and the packages that describe
a CPU (psutil, py-cpuinfo), which is most of the install size: with it, expect
roughly 180 MB. Without the extra, calling the benchmark suite tells you what to
install instead of failing obscurely, and nothing else is affected.

**The CLI** adds the `counted_float` command. The command is always installed;
without the extra it reports what to install instead of producing a traceback.

Extras compose, so `counted-float[benchmarking,cli]` gets you everything.

## Quick start

`CountedFloat` is a drop-in replacement for the built-in `float`; it is "contagious", so results of
math operations involving a `CountedFloat` stay `CountedFloat`:

```python
from counted_float import CountedFloat

cf = CountedFloat(1.3)
f = 2.8

result = cf + f  # result = CountedFloat(4.1)

is_float_1 = isinstance(cf, float)  # True
is_float_2 = isinstance(result, float)  # True
```

FLOPs performed by `CountedFloat` values are counted while a `FlopCountingContext` is active:

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

## Performance overhead

`CountedFloat` adds counting overhead in two forms — the price of Python-level
operator dispatch and result wrapping. How much slower your code runs depends
almost entirely on its operation mix:

- **native float ops** (`+`, `-`, `*`, `/`, comparisons): the expensive end of
  the range — the fixed per-operation dispatch cost dwarfs the nanoseconds of
  actual arithmetic;
- **patched `math.*` calls** (`math.sqrt`, `math.lgamma`, …): a roughly fixed
  surcharge per call, so the multiple shrinks as the function itself gets more
  expensive.

`counted_float evaluate-overhead` measures your own machine — a per-flop-type
overhead table, the geomean across types, and a practical mixed workload; see
the [captured example](https://counted-float.readthedocs.io/en/latest/benchmarking/#performance-impact)
for representative figures.

Three facts worth knowing:

- counting state is **per-thread**: a `FlopCountingContext` measures only the
  thread that opened it (open one context per worker thread to measure
  multi-threaded code, and sum the results). Free-threaded builds (3.14t) are
  supported and CI-tested;
- the overhead is inherent and `PauseFlopCounting` does **not** reduce it
  (the instrumented operators still execute; only count registration stops) —
  the escape hatch for hot uncounted regions is converting back via
  `float(x)`;
- overhead never affects *count* accuracy — counts are exact regardless.

This makes `CountedFloat` a tool for research and prototyping code, not
production hot loops.

**numpy counting is an explicit non-goal**: `np.float64` (`float` subclass) scalars
work and count correctly, but mixing `CountedFloat` with numpy arrays raises `TypeError` rather
than silently returning uncounted results — see
[Known limitations](https://counted-float.readthedocs.io/en/latest/known_limitations/)
for the full boundary.

## Documentation

The [documentation site](https://counted-float.readthedocs.io/) covers the rest:

- [Counting FLOPs](https://counted-float.readthedocs.io/en/latest/counting_flops/) — the counting model, counting contexts, pausing
- [Math patching semantics](https://counted-float.readthedocs.io/en/latest/math_patching/) — how (and when) `math.*` functions are instrumented
- [FLOP weights](https://counted-float.readthedocs.io/en/latest/flop_weights/) — built-in consensus weights, configuring your own
- [Benchmarking](https://counted-float.readthedocs.io/en/latest/benchmarking/) — estimating flop weights on your own hardware
- [CLI reference](https://counted-float.readthedocs.io/en/latest/cli/) — using `counted_float` as a stand-alone command-line tool
- [Known limitations](https://counted-float.readthedocs.io/en/latest/known_limitations/) — what falls outside the counting model
- [Reference](https://counted-float.readthedocs.io/en/latest/flop_types/) — per-FLOP-type counting rules, methodology, CPU scope
