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
bottom-up, with one column per flop type. That table is wide — an abbreviated
slice (the ARM subtree, leading columns only) is shown here:

Options:

| Option | Description |
|---|---|
| `--key-filter TEXT` | Show only the sources whose key contains `TEXT` — e.g. `--key-filter arm` for the ARM subtree, or `--key-filter benchmarks` for measured sources only. Defaults to showing everything. `--key_filter` is accepted as well. |

<!-- BEGIN generated: cli-show-data-slice -->
```
[~] counted_float show-data
                                                                        MINUS       ABS      COMP       ADD       SUB  COPYSIGN       MUL       FMA       RND       F2I       I2F  …
ALL                                                                      0.44      0.70      0.98      1.00      1.00      1.16      1.40      1.70      1.80      1.92      1.93  …
 ├─arm                                                                   0.81      1.02      0.63      1.00      1.00      1.67      1.49      1.88      1.62      1.46      1.56  …
 │  ├─v8_x                                                               0.82      0.98      0.82      1.00      1.00      1.26      1.47      1.80      1.47      1.57      1.92  …
 │  │  ├─benchmarks                                                      0.66      0.96      0.68      1.00      1.00      1.14      1.44      1.62      1.44        /         /   …
 │  │  │  ├─apple_m1_github_actions                                      0.68      0.67      1.37      1.00      1.00      0.67      1.32      1.34      1.01        /         /   …
 │  │  │  ├─apple_m3_max_mbp16                                           0.90      0.90      1.66      1.00      1.00      0.89      1.50      1.49      1.24        /         /   …
 │  │  │  ├─apple_m3_mba15                                               0.90      0.90      1.66      1.00      1.00      0.89      1.49      1.49      1.24        /         /   …
 │  │  │  ├─aws_graviton_2_neoverse_n1_ec2_m6g_large                     0.46      1.47      0.38      1.00      1.00      1.80      1.39      1.86      2.00        /         /   …
 │  │  │  └─aws_graviton_3_neoverse_v1_ec2_m7g_large                     0.51      1.00      0.10      1.00      1.00      1.99      1.50      2.00      1.99        /         /   …
 │  │  └─specs                                                           1.00      1.00      1.00      1.00      1.00        /       1.50      2.00      1.50      1.73      2.12  …
         ⋮   (remaining ARM specs, the full x86 subtree, and 37 more flop-type columns omitted)
```
<!-- END generated: cli-show-data-slice -->

## Test performance of `CountedFloat` vs `float`

```
[~] counted_float benchmark-counted-float
```

See [Performance impact](benchmarking.md#performance-impact) for example
results.
