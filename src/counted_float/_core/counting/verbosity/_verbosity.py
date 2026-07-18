"""Verbosity levels for flop-counting contexts."""

from enum import StrEnum


class Verbosity(StrEnum):
    """How much a counting context reports about the flops it registers, as it registers them.

    ``OFF`` is the default and reports nothing; it is also the only level counting sites pay
    nothing for.  ``INFO`` logs one line per registered flop, with the source location that
    triggered it and, where the counting rule applied is not self-evident, a short rationale.
    """

    OFF = "off"
    INFO = "info"
