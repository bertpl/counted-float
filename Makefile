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
	@echo '  splash       			        Build splash screen using current version of package.'
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
	uv run pre-commit run --all-files

format:
	uv run ruff format .;
	uv run ruff check --fix .;

format-single-file:
	uv run ruff format ${file_path};
	uv run ruff check --fix ${file_path};

splash:
	./.github/scripts/create_splash.sh "$$(uv version --short)-dev";
