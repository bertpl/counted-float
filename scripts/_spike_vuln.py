"""TEMPORARY spike file -- deliberately vulnerable, to prove the CodeQL gate fails the build.

Deleted before anything merges. `sys.argv` is a taint source for CodeQL's Python queries, so
passing it into a shell trips py/command-line-injection from the default suite.
"""

import os
import sys


def run_it() -> None:
    os.system("echo " + sys.argv[1])
