# Release Notes

<!------------------------------------------------------------------------------------------------->
> ## v0.9.3
> *(under development)*
> > This release heavily focuses on rectifying, documenting and streamlining
> > How we use external flop latency data sources (analyses, spec sheets),
> > to improve reliability and consistency of these data sources with the goal 
> > & scope of the package.
<!------------------------------------------------------------------------------------------------->

### What's New
- Add document with rationale behind analysis scope (CPU architectures, FPU instructions, metrics, ...) & with rigorous references behind obtained data. 
- Add support for SSE2- and ARM-specific FPU instruction latencies in unified way with legacy x87 instructions

### Improvements
/ 

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
- add command line command `run_flops_benchmark` that is runnable after installing with `uv tool install ...` + add instructions to readme.
- add hierarchical organization of spec analyses & benchmark results, enabling weighting scheme where e.g. # of results per processor type / brand does not influence the overall weight of that category.
- rename flop_weight configuration methods
  - `get_flop_weights` --> `get_active_flop_weights`
  - `set_flop_weights` --> `set_active_flop_weights`
- add `notes` field to InstructionLatency class, to allow adding human-readable attribution of data source etc...
- add additional FPU specs for ARM v7 (Cortex A9), ARM v8 (Cortex A55, A76) and ARM v9 (Cortex X1, X2, X3)

### Improvements
- improve output formatting of benchmark results & improve conciseness of microbenchmark output ('operation' vs '1000 flops')
- allow missing data in instruction latency data (`specs` data-folder), in which case missing data is imputed from neighboring data.

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
- simplify numba optional dependency handling (renamed 'benchmarking' -> 'numba'), 
  all functionality is now usable with and without this optional dependency. 
  However, running benchmarks without numba will result in a warning, since results are expect to be wildly inaccurate. 
- improve test coverage generation by running coverage analysis in various settings (Python 3.10 & 3.13; with and without numba)

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
- add splash screen to README.md

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
- add links to GitHub code, issues, ... to pyproject.toml to show up on pypi.org

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
- initial feature-complete version
- full readme file with usage instructions
- full test suite & automatic badge generation for README.md

### Improvements
/

### Bug Fixes
/

### Internal
- initial CI/CD pipeline