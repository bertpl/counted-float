file_path=

help:
	@echo 'Commands:'
	@echo ''
	@echo '  help		                    Show this help message.'
	@echo ''
	@echo '  build		                    (Re)build package using uv.'
	@echo ''
	@echo '  test		                    Run pytest unit tests.'
	@echo '  format		                    Format source code using ruff.'
	@echo '  format-single-file             Format single file using ruff. Useful in e.g. PyCharm to automatically trigger formatting on file save.'
	@echo ''
	@echo 'Options:'
	@echo ''
	@echo '  format-single-file             - accepts `file_path=<path>` to pass the relative path of the file to be formatted.'

build:
	uv build;

test-benchmark-deps:
	# run tests WITH optional [benchmark] dependencies installed
	uv run --extra benchmark pytest ./tests -m "not requires_no_benchmark"


test-no-benchmark-deps:
	# run tests WITHOUT optional [benchmark] dependencies installed
	uv sync;
	uv run pytest ./tests/counting ./tests/shared -m "not requires_benchmark"


test: test-no-benchmark-deps test-benchmark-deps
	# run all tests

coverage:
	uv run --extra benchmark pytest ./tests -m "not requires_no_benchmark" --cov=./counted_float/ --cov-report=html

format:
	uvx ruff format .;
	uvx ruff check --fix .;

format-single-file:
	uvx ruff format ${file_path};
	uvx ruff check --fix ${file_path};
