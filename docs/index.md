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

## Where to go next

- [Counting FLOPs](counting_flops.md) — the `CountedFloat` class, the counting
  model, and counting contexts.
- [Math patching semantics](math_patching.md) — how (and when) `math.*`
  functions are instrumented.
- [FLOP weights](flop_weights.md) — the built-in consensus weights and how to
  configure your own.
- [Benchmarking](benchmarking.md) — estimating flop weights on your own
  hardware.
- [CLI reference](cli.md) — using `counted_float` as a stand-alone
  command-line tool.
- [Known limitations](known_limitations.md) — what falls outside the counting
  model.
- [Deprecations](deprecations.md) — the names scheduled for removal at the next
  major, and what replaces them.
