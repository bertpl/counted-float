"""Verbosity levels for flop-counting contexts."""

from enum import StrEnum


class Verbosity(StrEnum):
    """What a counting context reports about the flops it registers, as it registers them.

    ``OFF`` is the default and reports nothing; it is also the only level counting sites pay
    nothing for.  ``WARNING`` reports the operations that were seen but could not be counted.
    ``INFO`` additionally logs one line per registered flop, with the source location that
    triggered it and, where the counting rule applied is not self-evident, a short rationale.

    ``ERROR`` prints nothing, and raises `UncountedOperationError` at every operation that
    ``WARNING`` would report, so that a test reaching one fails.  It is an alternative to
    ``WARNING``, not a step on the ``WARNING``/``INFO`` scale: a thread has one level at a time,
    so ``ERROR`` cannot be combined with ``INFO``.
    """

    OFF = "off"
    WARNING = "warning"
    INFO = "info"
    ERROR = "error"
