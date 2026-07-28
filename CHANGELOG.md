# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 2.1.0 (2026-07-28)

### Changed

- running the flops benchmark suite now requires the `benchmarking` extra; without it the suite says what to install instead of producing results it already warned were unusable
- evaluating counting overhead has moved to `counted_float.evaluation.evaluate_counting_overhead`, since it measures the library rather than the machine; its printed report says "counting overhead" rather than "benchmark" to match
- the base install is now counting-only; running the flops benchmark suite needs the new `benchmarking` extra, which cuts an install that only counts from ~181 MB to ~17 MB
- the CLI command for measuring counting overhead is now `evaluate-overhead`, matching what it does rather than the machinery it uses

### Deprecated

- `counted_float.benchmarking.run_counted_float_benchmark` still resolves but now warns; it will be dropped at the next major
- the `benchmark-counted-float` CLI command is renamed `evaluate-overhead`; the old name still runs but warns, and will be dropped at the next major
- the `numba` extra is renamed `benchmarking`; the old name still resolves to the same set but will be dropped at the next major

### Fixed

- evaluating counting overhead no longer prints a cycles column that silently reported nanoseconds whenever the CPU frequency could not be read

## 2.0.5 (2026-07-26)

### Added

- the README and docs now show a bar chart of the built-in flop weights, comparing arm64 and x86 against the all-architecture consensus

## 2.0.4 (2026-07-25)

### Changed

- importing the package no longer pulls in numpy, rich, psutil or py-cpuinfo, cutting import time for counting-only use

### Fixed

- a benchmark slice that measures zero elapsed time no longer crashes the calibration; it now ramps up the execution count instead

## 2.0.3 (2026-07-25)

### Fixed

- re-entering a `PauseFlopCounting` block that is already active now fails immediately with a clear message, instead of corrupting the pause state and silently leaving counting paused
- subclassing `CountedFloat` now fails at class definition instead of silently producing wrong flop counts

## 2.0.2 (2026-07-24)

### Fixed

- a `CountedFloat` construction or integer conversion that raises — an int too large to become a float, or `int()`/`floor()`/`ceil()`/`trunc()`/`round()` of `inf`/`nan` — no longer leaves a phantom flop counted

## 2.0.1 (2026-07-24)

### Changed

- the `show-data` CLI output now closes with a note that its weights are model-relative estimates, linking the cost-model docs

### Fixed

- the built-in flop-weight data now loads under zipimport / zipapp / frozen installs (previously raised `AttributeError` there)

## 2.0.0 (2026-07-23)

### Added

- the flops benchmark now measures how `math.hypot` / `math.dist` latency scales with the number of coordinates, via new `HYPOT_XARG`, `DIST`, and `DIST_XARG` flop types
- the flops benchmark now measures `math.gamma`, `math.lgamma`, `math.erf` and `math.erfc`
- using a `FlopCountingContext` from a thread other than the one that opened it now raises instead of silently mixing state
- free-threaded Python builds (3.14t) are now officially supported and CI-tested; the `numba` extra needs numba 0.65 or newer there
- `FlopCountingContext(verbosity=...)` can log every flop as it is counted, with the source line that triggered it and why it was counted that way
- verbosity level `WARNING` reports the operations that could not be counted at all, once per call site, so a quietly incomplete count says so
- the docs now show, per benchmarked flop cost, the machine code the measurement isolates, with a discussion of what the weight does and does not include

### Changed

- flop-weight JSON files now key on stable identifiers instead of display labels; an unrecognized key now raises instead of silently degrading to a missing weight. Pre-2.0.0 label-keyed files (including your own saved benchmark results) no longer load and must be regenerated
- flop counting state is now per-thread: contexts measure only the thread that opened them, and pausing affects the calling thread only
- the CBRT weight now measures the bare libm call, no longer including numba-specific argument handling
- `round(x, n)` with a nonzero digit count now counts MUL + RND + DIV (scale, round, unscale) instead of a single RND
- dividing by a power-of-two constant now counts MUL instead of DIV, matching the exact reciprocal multiplication a compiler emits; dividing by 1.0 now counts nothing, as the division folds away entirely
- sign-exact identity constants now fold in all operators: `* 1.0`, `- 0.0` and `+ (-0.0)` count nothing, `* -1.0`, `/ -1.0` and `(-0.0) - x` count a bare MINUS, and `//`/`%`/`divmod` fold their division step like `/` — while the signed-zero near-misses (`+ 0.0`, `- (-0.0)`, `0.0 - x`) keep counting, exactly as a strict compiler behaves. The constant checks add roughly 10% to counting overhead, the price of model fidelity
- the trig (sin/cos/tan/atan/atan2) and asinh/acosh benchmarks now draw their inputs from general-case argument ranges, instead of extreme magnitudes that priced a costlier or cheaper special regime
- re-collected the complete built-in flop-weight dataset — 12 EC2 instance types, 5 CI runners and the 4 manually benchmarked machines — shipping real weights for every measured flop type, including the new hypot/dist arity, special-function, remainder and sumprod types; the Linux x86 CI runner's silicon changed from Intel Emerald Rapids to AMD EPYC 9V74, swapping that source 1-for-1
- `math.dist` and 3+-argument `math.hypot` are now counted as per-call + per-extra-coordinate flop types measured on the real overflow-safe algorithm, instead of decomposed flop chains
- `math.gamma`, `math.lgamma`, `math.erf`, `math.erfc` and `math.remainder` are now counted; the uninstrumented remainder of the `math` module is exactly the float-representation helpers
- `math.sumprod` is now counted, as a per-call + per-extra-element price measured on the extended-precision algorithm it really runs

### Fixed

- `math.sumprod` on counted values now computes the same extended-precision result as on plain floats, and no longer silently miscounts it as a naive multiply-add chain
- `show-data` group headers are now legible on every terminal theme; the docs' screenshots and data-derived content are now regenerated from live output and drift-tested

## 1.7.0 (2026-07-17)

### Added

- `math.degrees`, `math.radians`, `math.dist`, `math.fsum` and `math.copysign` are now counted; `copysign` gets its own benchmarked flop type

### Changed

- mixing `CountedFloat` with numpy arrays (or non-double numpy scalars) now raises `TypeError` instead of silently returning uncounted results; `np.float64` scalar operations now count correctly from either side. numpy counting is documented as an explicit non-goal.
- `CountedFloat` no longer accepts attribute assignment or weak references, matching plain `float` exactly.
- refreshed the built-in flop-weight dataset with re-collected measurements, adding `COPYSIGN` weights and two new CPU sources

### Removed

- `counted_float.benchmarking` is no longer re-exported from the package root; import it directly. `import counted_float` is roughly 1.7x faster as a result, and no longer loads numba eagerly.

### Fixed

- `math.hypot` with other than 2 arguments is now counted per its dimension instead of always as the 2-argument form
- `math.prod` no longer counts an extra multiply for its implicit start value

## 1.6.3 (2026-07-16)

### Fixed

- a micro-benchmark whose runs all measure zero elapsed time now omits the uncertainty from its report instead of crashing

## 1.6.2 (2026-07-16)

### Changed

- the built-in consensus weights ship precomputed, so the first weighted-cost call no longer parses the whole built-in dataset

### Fixed

- fix issue where NaN-valued flop weights would break a serialization round-trip
- the flop-weight display no longer scatters missing weights among the measured ones
- `FlopWeights.from_abs_flop_costs()` rejects a negative flop cost instead of silently producing a negative weight
- the docs now list the `show-data` options and state the `Fraction` limitation accurately (it holds only with the `Fraction` on the right)

## 1.6.1 (2026-07-16)

### Changed

- reading flop counts is several times faster; counts are unchanged
- `FlopWeights.from_abs_flop_costs()` raises a clear `ValueError` instead of a raw `KeyError` or `ZeroDivisionError`

### Fixed

- `BuiltInData` is now exported from the package root, so star imports and strict type checkers recognize it
- a `FlopCountingContext` that is re-entered, or resumed outside its `with` block, no longer produces silently wrong counts
- `set_active_flop_weights()` now stores a copy, so mutating the object you passed no longer changes the configured weights

## 1.6.0 (2026-07-15)

### Added

- `math.fma` (Python 3.13+) is now counted as a single fused multiply-add instead of a separate multiply and add
- the FLOPs benchmark now measures fused multiply-add (`FMA`)

### Changed

- refreshed the built-in flop-weight dataset with re-collected measurements, adding an `FMA` weight backed by both benchmarks and vendor spec sheets

### Fixed

- corrected a number of third-party instruction latencies that had been transcribed from the wrong table row, slightly adjusting the built-in flop weights

## 1.5.2 (2026-07-14)

### Changed

- `CountedFloat` operations and patched `math` functions carry roughly a third less counting overhead (leaner dispatch and result wrapping); counts are unchanged

## 1.5.1 (2026-07-14)

### Added

- the FLOPs benchmark now warns when it can't read the CPU frequency, since its per-op cycle figures are then effectively nanoseconds (flop-weight ratios are unaffected)

### Fixed

- patched `math` functions no longer leave a spurious flop count when the underlying call raises a domain or overflow error

## 1.5.0 (2026-07-14)

### Added

- the `show-data` CLI command accepts `--key-filter` in addition to the original `--key_filter`
- `run_flops_benchmark()` and `run_counted_float_benchmark()` accept a `verbose` flag to silence progress output

### Changed

- the FLOPs benchmark's "numba not installed" notice is now a `RuntimeWarning` (filterable and catchable) instead of printed text

## 1.4.2 (2026-07-13)

### Changed

- refreshed the entire built-in flop-weight dataset with measurements collected under the new interleaved benchmark scheme (adds a Graviton 5 / Neoverse V3 data point)
- `**` with a constant exponent now strength-reduces beyond the square: `x**0.5` counts SQRT, `x**-1` counts DIV, small int exponents count their multiply chain (e.g. `x**3` -> 2 MUL) instead of a full POW
- built-in consensus flop weights are now loaded lazily on first use, cutting `import counted_float` time roughly 3x

### Fixed

- `math.log(x, base)` with a plain-float base now counts LOG+MUL like an int base (the base is a precomputable constant), instead of charging a runtime DIV
- `counted_float.__version__` is now available, as Python packaging convention expects
- the `counted_float` CLI now exits with a clear "install counted-float[cli]" message instead of a raw traceback when the optional `cli` extra is missing
- the FLOPs benchmark now interleaves kernel execution and uses a low-quantile estimator, making measured weights robust to transient CPU contention and thermal drift (built-in M3 Max data re-measured accordingly)
- benchmark-derived flop weights are now floored to a small positive value, so a noisy run can no longer produce negative or invalid weights

## 1.4.1 (2026-07-13)

### Changed

- the package version is now derived from git at build time; development builds self-report PEP 440 dev versions (e.g. `1.4.1.devN+g<sha>`) instead of the previous release's version

## 1.4.0 (2026-07-12)

### Added

- counting support for `math.atan2`, `hypot`, `asin`/`acos`/`atan`, `expm1`/`log1p`, `fmod`, and `fabs`
- counting support for the hyperbolic functions `math.sinh`/`cosh`/`tanh` and `asinh`/`acosh`/`atanh`
- the FLOPs benchmark suite now measures the new higher-order operations

### Changed

- `int`/`bool` operands are now more systematically treated as compile-time constants: arithmetic, comparisons, and `**` with an integer operand no longer add an `I2F` conversion count (wrap a runtime integer in `CountedFloat(...)` to count it)
- refreshed the built-in flop-weight dataset: re-measured all benchmarked CPUs on a current toolchain, giving the newly added higher-order FLOP types measured weights and shifting existing weighted costs slightly (zen1 coverage now from an EPYC server part)

### Fixed

- `%`, `//`, `divmod()`, and unary `+` on a `CountedFloat` now count and stay `CountedFloat` (they previously returned a plain, uncounted `float`, silently breaking downstream counting)
- `FlopWeights.get_sorted_flop_types()` now orders types deterministically when some weights are missing (NaN)

## 1.3.0 (2026-07-12)

### Added

- `counted_float benchmark` can write results to a JSON file via `--output`

## 1.2.2 (2026-07-09)

### Fixed

- `run_flops_benchmark()` no longer crashes with `OverflowError` on modern numba versions
- corrected documentation errors (FLOP-type counting rules, configuration function names, default rounding mode, CPU coverage tables)
- nested or pre-paused `PauseFlopCounting` no longer resumes counting too early
- `CountedFloat` arithmetic and comparisons now delegate to the other operand like `float` does (e.g. `Fraction` interop no longer raises), and failed operations no longer pollute counts

## 1.2.1 (2026-07-06)

### Fixed

- bullet lists in the methodology pages of the documentation site now render correctly

## 1.2.0 (2026-07-06)

### Added

- official documentation site at [counted-float.readthedocs.io](https://counted-float.readthedocs.io/)

### Security

- added a security policy (`SECURITY.md`) with a private vulnerability reporting channel

## 1.1.4 (2026-07-06)

### Security

- release artifacts now ship with SLSA build provenance and a GitHub Release; provenance is verifiable with `gh attestation verify`

## 1.1.3 (2026-07-06)

### Changed

- adopt the Keep a Changelog format for this file

## 1.1.2 (2026-07-05)

### Changed

- raise minimum dependency versions to those with wheels across Python 3.11–3.14 (per-version floors); the previous floors (e.g. `numpy>=1.20`) never actually installed on supported Pythons
- restructure CI & test infrastructure (reusable test workflow, single `ci-gate` check, coverage gate + metrics)

## 1.1.1 (2026-07-05)

### Changed

- package now ships inline type information (fully annotated API + PEP 561 `py.typed` marker)
- add pre-commit hooks (ruff, file hygiene, codespell, actionlint, conventional commit messages) + `make lint`
- expand ruff rule set from isort-only to the full lint family set
- enable pydocstyle (Google convention) and clean up all docstrings
- add the ty type checker to pre-commit
- fix the README image-URL rewrite in CI dropping the file's trailing newline

## 1.1.0 (2026-07-05)

### Changed

- importing `counted_float` no longer monkey-patches the `math` module; patches now apply only while a `FlopCountingContext` is active
- remove undocumented `CountedFloat.get_global_flop_counts()` (read counts through a `FlopCountingContext` instead)

### Fixed

- flop-weight getters (built-in & configured) return deep defensive copies, so mutating a returned object can no longer corrupt shared state

## 1.0.5 (2026-07-04)

### Changed

- replace CI-generated versioned splash image with a static one, dropping the (broken) ImageMagick dependency from CI

## 1.0.4 (2026-07-04)

### Fixed

- patched `math.log` & `math.pow` no longer break their stdlib contracts for non-counted code (2-arg log form restored & counted; pow raises domain errors instead of returning complex)

## 1.0.3 (2025-11-07)

### Changed

- move to trunk-based development workflow with release branches

## 1.0.2 (2025-10-15)

### Changed

- Streamline naming of built-in data and create more consistent structure (given specs & benchmarks equal weight on x86 side)
- Tweak color schema of `show-data` CLI command for improved readability
- Upgrade ImageMagick 6 -> 7 in CI/CD pipeline
- Split some GH Actions and unify gh-pages uploading for improved efficiency & reliability

### Fixed

- update outdated Known Limitations section in readme
- avoid error when showing built-in data on very narrow terminals

## 1.0.1

_(version deleted)_

## 1.0.0 (2025-10-09)

### Added

- add `benchmark-counted-float` cli command to compare `float` vs `CountedFloat` performance + updated readme with instructions & results.s

### Changed

- Improve unit test coverage to ~99%

### Fixed

- update outdated Known Limitations section in readme

## 0.9.7 (2025-10-09)

### Added

- Add new, default `"10%"` rounding mode for flop weights, reflecting a balance between accuracy & readability, while conveying the message these are approximate at best.

### Changed

- Improve readability of built-in data visualization by using colored instead of grey bands.

### Fixed

- rename one wrongly named benchmark file (remove `gh_` as it was obtained locally and not using GitHub CI/CD).

## 0.9.6 (2025-10-09)

### Added

- add updated benchmark data
  - **arm**
    - ***Apple***: M1, M3, M3 Max, M4 Pro
    - ***Other***: Azure Cobalt 100 (Neoverse N2), AWS Graviton 2 (Neoverse N1), 3 (Neoverse V1), 4 (Neoverse V2)
  - **x86**
    - ***AMD***: Ryzen 1700x (zen1), Epyc zen3, zen4, zen5
    - ***Intel***: i7-8850U (Kaby Lake), i7-8700B (Coffee Lake), Xeon scalable Gen3 (Ice Lake SP), Gen4 (Sapphire Rapids), Gen5 (Emerald Rapids), Xeon 6 (Granite Rapids)
- remove legacy built-in benchmarks (V1 benchmarks) & remove support for related legacy data structures
- all filtering by `key` in `show-data` CLI command, using new `--key_filter` optional argument

### Changed

- Improve robustness of CPU frequency detection on various environments
  - Make implementation fail-safe for environments where info is not available. (e.g. some cloud environments)
  - Make implementation robust to different units (MHz vs GHz).  (e.g. Apple M3 vs M4)
  - Increase transparency for cases where data is missing or unreliable, by allowing None/null.
- Improve conversion instruction latency -> flop weights in case of missing data, improving correlation with benchmark results.

## 0.9.5 (2025-10-05)

### Added

- Add `FlopType.EXP`, `FlopType.LOG`, `FlopType.EXP10`, `FlopType.LOG10`, `FlopType.CBRT`, `FlopType.SIN`, `FlopType.COS`, `FlopType.TAN`
- Remove support for Python 3.10 - so we can assume `math.cbrt` is available
- Extend readme with detailed description of how each flop type is counted & analysed.

### Changed

- Remove outdated `get_default_empirical_flop_weights` & `get_default_theoretical_flop_weights`, as it's now advised to use `get_builtin_flop_weights` with custom filtering.
- Merge comparison `FlopType` members `EQUALS`, `GTE`, `LTE`, `CMP_ZERO` into single `COMP`  (compilers typically map these to the same instruction)
- Rename `FlopType.POW2` -> `FlopType.EXP2` for consistency
- Add estimated total time for running benchmark

## 0.9.4 (2025-10-04)

### Added

- Differentiate between different rounding operations (float->float & float->int) and add counting of int->float where possible.
  - This introduces 2 new flop types: `F2I` and `I2F`

### Changed

- Make SystemInfo (sub-model of benchmark results) more complete & granular, providing explicit package info, OS info, ...
- Also capture cpu frequency after each benchmark run & estimate cpu latencies, allowing to extract benchmark durations in terms of nanoseconds or cpu cycles (q25, q50, q75)
- Replace flops benchmarking methods to ensure we test full end-to-end latency, instead of throughput, by ensuring all operations form dependent chains

## 0.9.3 (2025-09-28)

### Added

- Add document with rationale behind analysis scope (CPU architectures, FPU instructions, metrics, ...) & with rigorous references behind obtained data.
- Add various instruction latencies based on uops.info, Agner Fog & Intel/AMD/ARM spec sheets + reorganize data
- Add documentation on ecosystem of x86/arm ISAs, cores & cpus + provide rationale for selection of included data

### Changed

- Replace all x87-ISA based latency data & models with SSE2- or ARM-based data & data models
- Allow partially missing latency data (e.g. missing min_cycles)
- Normalize flop weights just on ADD flop type, for simplicity

## 0.9.2 (2025-09-20)

### Added

- Add estimation of CPU latencies for benchmark results & show while running benchmark
- Show uncertainty as % when benchmarking
- Add CLI command `show-data`

### Changed

- Add CPU frequency to benchmark system_info.
- Rename installed command `run_flops_benchmark` -> `counted_float`
- Simplify internal package folder structure (no changes in user-facing import paths)

## 0.9.1 (2025-09-18)

### Added

- Add command line command `run_flops_benchmark` that is runnable after installing with `uv tool install ...` + add instructions to readme.
- Add hierarchical organization of spec analyses & benchmark results, enabling weighting scheme where e.g. # of results per processor type / brand does not influence the overall weight of that category.
- Rename flop_weight configuration methods
  - `get_flop_weights` --> `get_active_flop_weights`
  - `set_flop_weights` --> `set_active_flop_weights`
- Add `notes` field to InstructionLatency class, to allow adding human-readable attribution of data source etc...
- Add additional FPU specs for ARM v7 (Cortex A9), ARM v8 (Cortex A55, A76) and ARM v9 (Cortex X1, X2, X3)

### Changed

- Improve output formatting of benchmark results & improve conciseness of microbenchmark output ('operation' vs '1000 flops')
- Allow missing data in instruction latency data (`specs` data-folder), in which case missing data is imputed from neighboring data.
- CI/CD - fix bug with custom PAT

## 0.9.0 (skipped)

_Removed for avoiding including documents that are public but intended to be mirrored._

_See 0.9.1._

## 0.8.4 (2025-09-13)

### Added

- Add release notes

### Changed

- CI/CD - Allow manual test deployments
- CI/CD - Use custom PAT for git actions to allow improved rulesets

## 0.8.3 (2025-09-06)

### Changed

- Simplify numba optional dependency handling (renamed 'benchmarking' -> 'numba'),
  all functionality is now usable with and without this optional dependency.
  However, running benchmarks without numba will result in a warning, since results are expect to be wildly inaccurate.
- Improve test coverage generation by running coverage analysis in various settings (Python 3.10 & 3.13; with and without numba)

## 0.8.2 (2025-09-05)

### Added

- Add splash screen to README.md

### Changed

- clean up CI/CD pipeline

## 0.8.1 (2025-08-12)

### Changed

- Add links to GitHub code, issues, ... to pyproject.toml to show up on pypi.org

## 0.8.0 (2025-08-11)

### Added

- Initial feature-complete version
- Full readme file with usage instructions
- Full test suite & automatic badge generation for README.md

### Changed

- Initial CI/CD pipeline
