"""TEMPORARY spike file -- deliberately vulnerable, to prove the CodeQL gate fails the build.

Deleted before anything merges. Several unrelated patterns, so the gate is proven by whichever
of them the default query suite actually reports.
"""

import os
import socket
import subprocess
import sys
import tempfile


def taint_into_shell() -> None:
    """py/command-line-injection: sys.argv is a taint source, os.system a shell sink."""
    os.system("echo " + sys.argv[1])


def taint_into_subprocess() -> None:
    """py/shell-command-constructed-from-input, via shell=True on a built string."""
    subprocess.call("ls " + sys.argv[1], shell=True)


def bind_every_interface() -> int:
    """py/bind-socket-all-network-interfaces: purely syntactic, no taint tracking needed."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 8080))
    return s.fileno()


def racy_temp_file() -> str:
    """py/insecure-temporary-file: mktemp is the classic TOCTOU temp-file bug."""
    return tempfile.mktemp()
