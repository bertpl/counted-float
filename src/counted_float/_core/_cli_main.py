"""Console-script entry point with a guard for the optional ``cli`` extra.

The ``counted_float`` script is installed unconditionally, but the CLI itself
needs ``click``, which only comes with the ``cli`` extra — so the click-based
module is imported lazily and a missing ``click`` yields an actionable message
instead of a raw traceback.
"""

import sys

from counted_float._core.compatibility import CLI


def main() -> None:
    """Run the click-based CLI, or exit with install guidance when click is missing."""
    try:
        from counted_float._core._cli import cli
    except ModuleNotFoundError as e:
        if CLI.explains(e):
            sys.stderr.write(f"{CLI.missing_dependency_message()}\n")
            raise SystemExit(1) from None
        raise
    cli()
