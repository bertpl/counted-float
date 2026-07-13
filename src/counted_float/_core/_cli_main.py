"""Console-script entry point with a guard for the optional ``cli`` extra.

The ``counted_float`` script is installed unconditionally, but the CLI itself
needs ``click``, which only comes with the ``cli`` extra — so the click-based
module is imported lazily and a missing ``click`` yields an actionable message
instead of a raw traceback.
"""

import sys


def main() -> None:
    """Run the click-based CLI, or exit with install guidance when click is missing."""
    try:
        from counted_float._core._cli import cli
    except ModuleNotFoundError as e:
        if e.name == "click":
            sys.stderr.write('The counted_float CLI requires the "cli" extra: pip install "counted-float[cli]"\n')
            raise SystemExit(1) from None
        raise
    cli()
