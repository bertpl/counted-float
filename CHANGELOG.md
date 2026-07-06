# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

### Changed

### Deprecated

### Removed

### Fixed

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
