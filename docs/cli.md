# CLI reference

## Installing the package as a command-line tool

An alternative way of using (parts of) the functionality is installing the
package as a stand-alone command-line tool using `uv` or `pipx`:

```
uv tool install git+https://github.com/bertpl/counted-float@main[numba,cli]         # latest official release
uv tool install git+https://github.com/bertpl/counted-float@develop[numba,cli]      # or latest develop version
```

This installs the `counted_float` command-line tool, which can be used to e.g.
run flops benchmarks. The `cli` optional dependency is only useful when
installing the package as a tool this way.

## Running benchmarks

```
counted_float benchmark
```

This runs the FLOPS benchmark suite on the current machine and prints the
full results as JSON: system information (processor, OS, Python, package
versions), benchmark settings, per-operation cycle counts, and the estimated
per-FLOP-type latencies. See [Benchmarking](benchmarking.md) for how the
suite works.

To also persist the results, pass `--output`:

```
counted_float benchmark --output results.json
```

This writes the same results to the given path, in the same JSON schema as
the package's [built-in data files](builtin_data.md) — so results collected
this way can be inspected, shared, or compared against the built-in entries.

## Show built-in data

`show-data` renders the full weight hierarchy: every data source, aggregated
bottom-up, across all 36 flop-type columns. That table is wide — an abbreviated
slice (the ARM subtree, leading columns only) is shown here:

```
[~] counted_float show-data
                                                                        MINUS       ABS      COMP       ADD       SUB       MUL       RND       F2I       I2F       DIV      FMOD  …
ALL                                                                      0.40      0.71      0.95      1.00      1.00      1.39      1.76      1.87      1.87      5.38      6.00  …
 ├─arm                                                                   0.85      1.03      0.61      1.00      1.00      1.44      1.55      1.43      1.53      5.79      7.40  …
 │  ├─v8_x                                                               0.75      0.93      0.60      1.00      0.98      1.37      1.37      1.43      1.76      5.20      6.56  …
 │  │  ├─benchmarks                                                      0.56      0.86      0.36      1.00      0.96      1.26      1.24        /         /       3.60      5.43  …
 │  │  │  ├─apple_m1_github_actions                                      0.51      0.48      0.90      1.00      0.79      0.97      0.56        /         /       2.55      3.59  …
 │  │  │  ├─apple_m3_max_mbp16                                           0.49      0.76      1.04      1.00      1.03      1.05      1.08        /         /       1.82      3.58  …
 │  │  │  ├─apple_m3_mba15                                               0.90      0.90      1.66      1.00      1.00      1.50      1.24        /         /       3.97      6.22  …
 │  │  │  ├─aws_graviton_2_neoverse_n1_ec2_m6g_large                     0.46      1.47      0.39      1.00      1.00      1.38      2.00        /         /       5.41      7.27  …
 │  │  │  └─aws_graviton_3_neoverse_v1_ec2_m7g_large                     0.51      1.00      0.01      1.00      1.00      1.50      1.99        /         /       6.04      8.13  …
 │  │  └─specs                                                           1.00      1.00      1.00      1.00      1.00      1.50      1.50      1.73      2.12      7.50        /  …
         ⋮   (remaining ARM specs, the full x86 subtree, and 25 more flop-type columns omitted)
```

## Test performance of `CountedFloat` vs `float`

```
[~] counted_float benchmark-counted-float
```

See [Performance impact](benchmarking.md#performance-impact) for example
results.
