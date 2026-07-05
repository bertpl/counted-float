"""Flop-weight configuration API: get and set the active, built-in, and default consensus flop weights."""

from counted_float._core.counting.config import (
    get_active_flop_weights,
    get_builtin_flop_weights,
    get_default_consensus_flop_weights,
    set_active_flop_weights,
)

__all__ = [
    "get_active_flop_weights",
    "get_builtin_flop_weights",
    "get_default_consensus_flop_weights",
    "set_active_flop_weights",
]
