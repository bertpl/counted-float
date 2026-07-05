# Change Log

<!------------------------------------------------------------------------------------------------->
> ## v1.1.1
> *(2026-07-05)*
> > Quality-tooling release: pre-commit hooks, expanded ruff rule set, ty type checker; package now ships type information.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
- package now ships inline type information (fully annotated API + PEP 561 `py.typed` marker)

### Bug Fixes
/

### Internal
- add pre-commit hooks (ruff, file hygiene, codespell, actionlint, conventional commit messages) + `make lint`
- expand ruff rule set from isort-only to the full lint family set
- enable pydocstyle (Google convention) and clean up all docstrings
- add the ty type checker to pre-commit
- fix the README image-URL rewrite in CI dropping the file's trailing newline

<!------------------------------------------------------------------------------------------------->
> ## v1.1.0
> *(2026-07-05)*
> > Well-behaved importing: no more monkey-patching at load time.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
- importing `counted_float` no longer monkey-patches the `math` module; patches now apply only while a `FlopCountingContext` is active

### Bug Fixes
- flop-weight getters (built-in & configured) return deep defensive copies, so mutating a returned object can no longer corrupt shared state

### Internal
- remove undocumented `CountedFloat.get_global_flop_counts()` (read counts through a `FlopCountingContext` instead)

<!------------------------------------------------------------------------------------------------->
> ## v1.0.5
> *(2026-07-04)*
> > CI fix release: repair badge & splash publishing.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
/

### Bug Fixes
/

### Internal
- replace CI-generated versioned splash image with a static one, dropping the (broken) ImageMagick dependency from CI

<!------------------------------------------------------------------------------------------------->
> ## v1.0.4
> *(2026-07-04)*
> > Bug-fix release: restore stdlib contracts of patched `math` functions.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
/

### Bug Fixes
- patched `math.log` & `math.pow` no longer break their stdlib contracts for non-counted code (2-arg log form restored & counted; pow raises domain errors instead of returning complex)

### Internal
/

<!------------------------------------------------------------------------------------------------->
> ## v1.0.3
> *(2025-11-07)*
> > CI & overall development workflow update.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
/

### Bug Fixes
/

### Internal
- move to trunk-based development workflow with release branches

<!------------------------------------------------------------------------------------------------->
> ## v1.0.2
> *(2025-10-15)*
> > Minor bug fixes & improvements release.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
- Streamline naming of built-in data and create more consistent structure (given specs & benchmarks equal weight on x86 side)
- Tweak color schema of `show-data` CLI command for improved readability

### Bug Fixes
- update outdated Known Limitations section in readme
- avoid error when showing built-in data on very narrow terminals

### Internal
- Upgrade ImageMagick 6 -> 7 in CI/CD pipeline
- Split some GH Actions and unify gh-pages uploading for improved efficiency & reliability

<!------------------------------------------------------------------------------------------------->
> ## v1.0.1
<!------------------------------------------------------------------------------------------------->
*(version deleted)*


<!------------------------------------------------------------------------------------------------->
> ## v1.0.0
> *(2025-10-09)*
> > Final details to justify bump to v1.0.0.
<!------------------------------------------------------------------------------------------------->

### What's New
- add `benchmark-counted-float` cli command to compare `float` vs `CountedFloat` performance + updated readme with instructions & results.s

### Improvements
/

### Bug Fixes
- update outdated Known Limitations section in readme

### Internal
- Improve unit test coverage to ~99%


<!------------------------------------------------------------------------------------------------->
> ## v0.9.7
> *(2025-10-09)*
> > Relatively minor update release, with a few quality-of-life improvements.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add new, default `"10%"` rounding mode for flop weights, reflecting a balance between accuracy & readability, while conveying the message these are approximate at best.

### Improvements
- Improve readability of built-in data visualization by using colored instead of grey bands.

### Bug Fixes
- rename one wrongly named benchmark file (remove `gh_` as it was obtained locally and not using GitHub CI/CD).

### Internal
/

<!------------------------------------------------------------------------------------------------->
> ## v0.9.6
> *(2025-10-09)*
> > Given the changes of previous versions, this release updates & extends benchmark data, resulting in a total of 19 benchmarks (8 x arm, 11 x x86).
<!------------------------------------------------------------------------------------------------->

### What's New
- add updated benchmark data
  - **arm**
    - ***Apple***: M1, M3, M3 Max, M4 Pro
    - ***Other***: Azure Cobalt 100 (Neoverse N2), AWS Graviton 2 (Neoverse N1), 3 (Neoverse V1), 4 (Neoverse V2)
  - **x86**
    - ***AMD***: Ryzen 1700x (zen1), Epyc zen3, zen4, zen5
    - ***Intel***: i7-8850U (Kaby Lake), i7-8700B (Coffee Lake), Xeon scalable Gen3 (Ice Lake SP), Gen4 (Sapphire Rapids), Gen5 (Emerald Rapids), Xeon 6 (Granite Rapids)
- remove legacy built-in benchmarks (V1 benchmarks) & remove support for related legacy data structures
- all filtering by `key` in `show-data` CLI command, using new `--key_filter` optional argument

### Improvements
- Improve robustness of CPU frequency detection on various environments
  - Make implementation fail-safe for environments where info is not available. (e.g. some cloud environments)
  - Make implementation robust to different units (MHz vs GHz).  (e.g. Apple M3 vs M4)
  - Increase transparency for cases where data is missing or unreliable, by allowing None/null.
- Improve conversion instruction latency -> flop weights in case of missing data, improving correlation with benchmark results.

### Bug Fixes
/

### Internal
/


<!------------------------------------------------------------------------------------------------->
> ## v0.9.5
> *(2025-10-05)*
> > This release focuses on simplifying & extending the modelled FlopTypes.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add `FlopType.EXP`, `FlopType.LOG`, `FlopType.EXP10`, `FlopType.LOG10`, `FlopType.CBRT`, `FlopType.SIN`, `FlopType.COS`, `FlopType.TAN`
- Remove support for Python 3.10 - so we can assume `math.cbrt` is available
- Extend readme with detailed description of how each flop type is counted & analysed.


### Improvements
- Remove outdated `get_default_empirical_flop_weights` & `get_default_theoretical_flop_weights`, as it's now advised to use `get_builtin_flop_weights` with custom filtering.
- Merge comparison `FlopType` members `EQUALS`, `GTE`, `LTE`, `CMP_ZERO` into single `COMP`  (compilers typically map these to the same instruction)
- Rename `FlopType.POW2` -> `FlopType.EXP2` for consistency
- Add estimated total time for running benchmark

### Bug Fixes
/

### Internal
/

<!------------------------------------------------------------------------------------------------->
> ## v0.9.4
> *(2025-10-04)*
> > This release focuses on rectifying the benchmarking setup, where it is important to test execution ***latency***
> > rather than ***throughput***.
<!------------------------------------------------------------------------------------------------->

### What's New
- Differentiate between different rounding operations (float->float & float->int) and add counting of int->float where possible.
  - This introduces 2 new flop types: `F2I` and `I2F`

### Improvements
- Make SystemInfo (sub-model of benchmark results) more complete & granular, providing explicit package info, OS info, ...
- Also capture cpu frequency after each benchmark run & estimate cpu latencies, allowing to extract benchmark durations in terms of nanoseconds or cpu cycles (q25, q50, q75)
- Replace flops benchmarking methods to ensure we test full end-to-end latency, instead of throughput, by ensuring all operations form dependent chains

### Bug Fixes
/

### Internal
/

<!------------------------------------------------------------------------------------------------->
> ## v0.9.3
> *(2025-09-28)*
> > This release heavily focuses on rectifying, documenting and streamlining
> > How we use external flop latency data sources (analyses, spec sheets),
> > to improve reliability and consistency of these data sources with the goal
> > & scope of the package.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add document with rationale behind analysis scope (CPU architectures, FPU instructions, metrics, ...) & with rigorous references behind obtained data.
- Add various instruction latencies based on uops.info, Agner Fog & Intel/AMD/ARM spec sheets + reorganize data
- Add documentation on ecosystem of x86/arm ISAs, cores & cpus + provide rationale for selection of included data

### Improvements
- Replace all x87-ISA based latency data & models with SSE2- or ARM-based data & data models
- Allow partially missing latency data (e.g. missing min_cycles)
- Normalize flop weights just on ADD flop type, for simplicity

### Bug Fixes
/

### Internal
/

<!------------------------------------------------------------------------------------------------->
> ## v0.9.2
> *(2025-09-20)*
>
> > Add functionality for creating more clarity on included data & estimated cpu latencies
> > while benchmarking.  This should make it easier to perform sanity checks on built-in data
> > and interpret results.  This is a precursor to improving overall quality of both benchmarking
> > and data based on external analyses / spec sheets.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add estimation of CPU latencies for benchmark results & show while running benchmark
- Show uncertainty as % when benchmarking
- Add CLI command `show-data`

### Improvements
- Add CPU frequency to benchmark system_info.
- Rename installed command `run_flops_benchmark` -> `counted_float`

### Bug Fixes
/

### Internal
- Simplify internal package folder structure (no changes in user-facing import paths)


<!------------------------------------------------------------------------------------------------->
> ## v0.9.1
> *(2025-09-18)*
> > Structural change in how built-in data is stored (flexible hierarchical structure) + allow missing data.
> > This is a step towards future-proofing the design for later inclusion of additional data sources.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add command line command `run_flops_benchmark` that is runnable after installing with `uv tool install ...` + add instructions to readme.
- Add hierarchical organization of spec analyses & benchmark results, enabling weighting scheme where e.g. # of results per processor type / brand does not influence the overall weight of that category.
- Rename flop_weight configuration methods
  - `get_flop_weights` --> `get_active_flop_weights`
  - `set_flop_weights` --> `set_active_flop_weights`
- Add `notes` field to InstructionLatency class, to allow adding human-readable attribution of data source etc...
- Add additional FPU specs for ARM v7 (Cortex A9), ARM v8 (Cortex A55, A76) and ARM v9 (Cortex X1, X2, X3)

### Improvements
- Improve output formatting of benchmark results & improve conciseness of microbenchmark output ('operation' vs '1000 flops')
- Allow missing data in instruction latency data (`specs` data-folder), in which case missing data is imputed from neighboring data.

### Bug Fixes
/

### Internal
- CI/CD - fix bug with custom PAT

<!------------------------------------------------------------------------------------------------->
> ## v0.9.0
> *(skipped)*
> > Removed for avoiding including documents that are public but intended to be mirrored.
<!------------------------------------------------------------------------------------------------->

--> *See v0.9.1*

<!------------------------------------------------------------------------------------------------->
> ## v0.8.4
> *(2025-09-13)*
> > Further improvements for more complete look on pypi.org, with added release notes + internal cleanup.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add release notes

### Improvements
/

### Bug Fixes
/

### Internal
- CI/CD - Allow manual test deployments
- CI/CD - Use custom PAT for git actions to allow improved rulesets

<!------------------------------------------------------------------------------------------------->
> ## v0.8.3
> *(2025-09-06)*
> > Improved handling of optional dependencies, exposing the entire feature set,
> > independent of the installed optional dependencies.  Also represent significant internal simplification.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
- Simplify numba optional dependency handling (renamed 'benchmarking' -> 'numba'),
  all functionality is now usable with and without this optional dependency.
  However, running benchmarks without numba will result in a warning, since results are expect to be wildly inaccurate.
- Improve test coverage generation by running coverage analysis in various settings (Python 3.10 & 3.13; with and without numba)

### Bug Fixes
/

### Internal
/

<!------------------------------------------------------------------------------------------------->
> ## v0.8.2
> *(2025-09-05)*
> > Add splash screen, mostly for visual appeal on pypi.org & github.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add splash screen to README.md

### Improvements
/

### Bug Fixes
/

### Internal
- clean up CI/CD pipeline

<!------------------------------------------------------------------------------------------------->
> ## v0.8.1
> *(2025-08-12)*
> > Small improvements for more complete look on pypi.org.
<!------------------------------------------------------------------------------------------------->

### What's New
/

### Improvements
- Add links to GitHub code, issues, ... to pyproject.toml to show up on pypi.org

### Bug Fixes
/

### Internal
/

<!------------------------------------------------------------------------------------------------->
> ## v0.8.0
> *(2025-08-11)*
> > This is the initial release, supporting flop counting & benchmarking.
<!------------------------------------------------------------------------------------------------->

### What's New
- Initial feature-complete version
- Full readme file with usage instructions
- Full test suite & automatic badge generation for README.md

### Improvements
/

### Bug Fixes
/

### Internal
- Initial CI/CD pipeline
