file_path=

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
	@echo '  test-collect-ids              List the collected test node-ids (CI unions these across matrix legs).'
	@echo '  lint		                    Run all pre-commit hooks on all files.'
	@echo '  mutation		                Run local mutation testing (mutmut). MODULE=<substr> scopes it.'
	@echo '  mutation-results	            List the surviving mutants from the last mutation run.'
	@echo '  mutation-stats	                Export the last mutation run'"'"'s tallies as JSON (used by the release badge).'
	@echo '  format		                    Format source code using ruff.'
	@echo '  format-single-file             Format single file using ruff. Useful in e.g. PyCharm to automatically trigger formatting on file save.'
	@echo ''
	@echo '  precompute-weights            Regenerate the shipped consensus flop weights from the built-in source data.'
	@echo '  regen-docs                    Regenerate the dataset-derived docs content (marked text blocks + screenshots).'
	@echo '  regen-machine-code            Regenerate the benchmark-probe machine-code listings (ARM64 machine only).'
	@echo ''
	@echo '  release       		            Release a version: make release VERSION=X.Y.Z (validates, bumps, tags, pushes).'
	@echo ''
	@echo 'Options:'
	@echo ''
	@echo '  format-single-file             - accepts `file_path=<path>` to pass the relative path of the file to be formatted.'
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

format:
	uv run ruff format .;
	uv run ruff check --fix .;

format-single-file:
	uv run ruff format ${file_path};
	uv run ruff check --fix ${file_path};

# local mutation testing over _core (config in [tool.mutmut]); MODULE=<substr> scopes to matching mutants
mutation:
	uv run --group mutation --all-extras --python 3.13 mutmut run $(if $(MODULE),"*$(MODULE)*",)

mutation-results:
	uv run --group mutation --all-extras --python 3.13 mutmut results

# machine-readable killed/survived/total of the last run -> mutants/mutmut-cicd-stats.json (release.py reads it)
mutation-stats:
	uv run --group mutation --all-extras --python 3.13 mutmut export-cicd-stats

precompute-weights:
	uv run python scripts/generate_precomputed_weights.py

regen-docs:
	uv run python scripts/generate_docs_content.py

regen-machine-code:
	uv run --all-extras python scripts/generate_machine_code_docs.py

# DRY_RUN=1 stops after the preconditions (mutation measurement included), writing nothing
release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=X.Y.Z [DRY_RUN=1]" && exit 1)
	$(MAKE) test
	uv run python scripts/release.py $(VERSION) $(if $(DRY_RUN),--dry-run,)
