# Release Notes

<!------------------------------------------------------------------------------------------------->
## v0.8.4
*(under development)*
<!------------------------------------------------------------------------------------------------->

### What's New
- Add release notes

### Improvements
/

### Bug Fixes
/

### Internal
- CI/CD - Allow manual test deployments


<!------------------------------------------------------------------------------------------------->
## v0.8.3
*(2025-09-06)*
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
## v0.8.2
*(2025-09-05)*
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
## v0.8.1
*(2025-08-12)*
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
## v0.8.0
*(2025-08-11)*
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