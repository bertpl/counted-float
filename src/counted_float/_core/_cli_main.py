"""Console-script entry point with a guard for the optional ``cli`` extra.

The ``counted_float`` script is installed unconditionally, but the CLI itself
needs ``click``, which only comes with the ``cli`` extra — so the click-based
module is imported lazily and a missing ``click`` yields an actionable message
instead of a raw traceback.
"""

import sys

from counted_float._core.compatibility import CAP_CLI, MissingCapabilityError, requires


def main() -> None:
    """Run the click-based CLI, or exit with install guidance when click is missing."""
    try:
        with requires(CAP_CLI):
            from counted_float._core._cli import cli
    except MissingCapabilityError as e:
        # a console script printing a traceback is a worse answer than the message itself
        sys.stderr.write(f"{e}\n")
        raise SystemExit(1) from None

    cli()
