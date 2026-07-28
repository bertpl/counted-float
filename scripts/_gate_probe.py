"""TEMPORARY probe -- confirms the assembled gate goes red. Deleted with its branch."""

import socket
import tempfile


def bind_every_interface() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 8080))
    return s.fileno()


def racy_temp_file() -> str:
    return tempfile.mktemp()
