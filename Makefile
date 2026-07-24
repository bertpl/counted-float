file_path=

help:
	@echo 'Commands:'
	@echo ''
	@echo '  help		                    Show this help message.'
	@echo ''
	@echo '  build		                    (Re)build package using uv.'
	@echo ''
	@echo '  test		                    Run pytest unit tests.'
	@echo '  lint		                    Run all pre-commit hooks on all files.'
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

build:
	uv build;

test:
	# run all tests - with numba & just 1 python version
	uv run --all-extras --python 3.13 pytest ./tests

lint:
	# reconcile the venv to the lockfile first, so the hooks run the pinned ruff/ty -- not whatever a
	# prior `uv run --exact` or interpreter switch left behind, which would drift make lint from CI
	uv sync --locked --all-extras
	uv run pre-commit run --all-files

format:
	uv run ruff format .;
	uv run ruff check --fix .;

format-single-file:
	uv run ruff format ${file_path};
	uv run ruff check --fix ${file_path};

precompute-weights:
	uv run python scripts/generate_precomputed_weights.py

regen-docs:
	uv run python scripts/generate_docs_content.py

regen-machine-code:
	uv run --all-extras python scripts/generate_machine_code_docs.py

release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=X.Y.Z" && exit 1)
	$(MAKE) test
	uv run python scripts/release.py $(VERSION)
