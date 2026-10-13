"""Verbosity levels for flop-counting contexts."""

from enum import StrEnum


class Verbosity(StrEnum):
    """A Verbosity level sets what a counting context reports while it counts flops, and whether it raises.

    ``OFF`` is the default and reports nothing; it is also the only level counting sites pay
    nothing for.  ``WARNING`` reports the operations that were seen but could not be counted.
    ``INFO`` additionally logs one line per registered flop, with the source location that
    triggered it and, where the counting rule applied is not self-evident, a short rationale.

    ``ERROR`` treats an operation that could not be counted as an error: it raises
    `UncountedOperationError` at every operation that ``WARNING`` would report, so that a test
    reaching one fails, and prints nothing.  Unlike the ``ERROR`` level of Python's ``logging``,
    it does not print a subset of the ``WARNING`` lines.  A thread has one level at a time, so
    ``ERROR`` cannot be combined with ``INFO``.
    """

    OFF = "off"
    WARNING = "warning"
    INFO = "info"
    ERROR = "error"
