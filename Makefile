# Comments sit above their target rather than inside the recipe: CI runs the test targets on
# Windows too, where make drives cmd.exe, which does not understand `#`.

# Knobs for the test and lint targets. CI varies these per matrix leg by passing them on the
# make command line; a bare `make test` / `make lint` uses the defaults.
PYTHON ?= 3.13
RESOLUTION ?= highest
ALL_EXTRAS ?= true
PYTEST_ARGS ?=
PRE_COMMIT_ARGS ?=

# The single definition of the environment the suite runs in, shared by both test targets.
# --exact prunes whatever a previous target installed, so this environment matches CI's rather
# than merely satisfying it; --no-default-groups is what actually narrows, since --group alone
# only adds to the default set.
UV_RUN_TEST = uv run --exact --no-default-groups --group test \
              --python $(PYTHON) --resolution $(RESOLUTION) \
              $(if $(filter true,$(ALL_EXTRAS)),--all-extras,)

help:
	@echo 'Commands:'
	@echo ''
	@echo '  help		                    Show this help message.'
	@echo ''
	@echo '  build		                    (Re)build package using uv.'
	@echo ''
	@echo '  test		                    Run pytest unit tests.'
	@echo '  test-collect-ids               List the collected test node-ids (CI unions these across matrix legs).'
	@echo '  lint		                    Run all pre-commit hooks on all files. Formats and applies ruff fixes as it goes.'
	@echo '  mutation		                Run local mutation testing (mutmut). MODULE=<substr> scopes it.'
	@echo '  mutation-results	            List the surviving mutants from the last mutation run.'
	@echo '  mutation-stats	                Export the last mutation run'"'"'s tallies as JSON (used by the release badge).'
	@echo ''
	@echo '  precompute-weights            Regenerate the shipped consensus flop weights from the built-in source data.'
	@echo '  regen-docs                    Regenerate the dataset-derived docs content (marked text blocks + screenshots).'
	@echo '  regen-machine-code            Regenerate the benchmark-probe machine-code listings (ARM64 machine only).'
	@echo ''
	@echo '  release       		            Release a version: make release VERSION=X.Y.Z (validates, bumps, tags, pushes).'
	@echo ''
	@echo 'Options:'
	@echo ''
	@echo '  test, test-collect-ids         - accept PYTHON=<x.y>, RESOLUTION=highest|lowest-direct, ALL_EXTRAS=true|false, PYTEST_ARGS=<args>.'
	@echo '  lint                           - accepts PRE_COMMIT_ARGS=<args>.'

build:
	uv build;

test:
	$(UV_RUN_TEST) pytest ./tests $(PYTEST_ARGS)

# -o addopts= clears `-n auto`, so collection runs single-process (xdist off) and prints one
# node-id per line.
test-collect-ids:
	$(UV_RUN_TEST) pytest ./tests --collect-only -q -o addopts=

# uv sync reconciles the venv to the lockfile first, so the hooks run the pinned ruff/ty -- not
# whatever a prior `uv run --exact` or interpreter switch left behind. --all-extras matters for ty
# rather than for the linters: it type-checks the code behind every extra, so a package sitting
# behind one still has to be resolvable.
lint:
	uv sync --locked --all-extras
	uv run pre-commit run --all-files $(PRE_COMMIT_ARGS)

# local mutation testing over _core (config in [tool.mutmut]); MODULE=<substr> scopes to matching mutants
mutation:
	# the test-attribution map merges by test name, so a changed test that keeps its name keeps its
	# stale mapping -- and runs against the wrong mutants without any visible signal. Deleting the
	# map forces a fresh collection pass (~35s) so every run measures against current attribution.
	rm -f mutants/mutmut-stats.json
	uv run --group mutation --all-extras --python 3.13 mutmut run $(if $(MODULE),"*$(MODULE)*",)

mutation-results:
	uv run --group mutation --all-extras --python 3.13 mutmut results

# machine-readable killed/survived/total of the last run -> mutants/mutmut-cicd-stats.json (release.py reads it)
mutation-stats:
	uv run --group mutation --all-extras --python 3.13 mutmut export-cicd-stats

precompute-weights:
	uv run python scripts/generate_precomputed_weights.py

# A strict build fails on any warning -- a dead link, a bad nav entry -- instead of shipping it
# silently. It uses docs-only deps and no project, because the docs build runs no plugin that imports
# the package, matching the Read the Docs install. The target is declared .PHONY because the `docs/`
# source directory would otherwise mark the docs target up to date and skip it.
.PHONY: docs
docs:
	uv run --only-group docs mkdocs build --strict

regen-docs:
	uv run python scripts/generate_docs_content.py

regen-machine-code:
	uv run --all-extras python scripts/generate_machine_code_docs.py

# DRY_RUN=1 stops after the preconditions (mutation measurement included), writing nothing
release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=X.Y.Z [DRY_RUN=1]" && exit 1)
	$(MAKE) test
	uv run python scripts/release.py $(VERSION) $(if $(DRY_RUN),--dry-run,)
