"""The flops benchmark suite: what this package means, gated end to end.

Everything under here needs the benchmarking extra, so the sub-package resolves on first use rather
than on import. This module deliberately stays importable without it: a guard has to be reachable to
be able to report anything, and the public package re-exports through here on installs with no
extras at all.

FlopsBenchmarkResults is a plain model rather than part of the suite, so it comes straight from its
own package and stays eagerly available: reading a stored result needs no extra.
"""

from typing import TYPE_CHECKING, Any

from counted_float._core.compatibility import Capability
from counted_float._core.models import FlopsBenchmarkResults

from ._runner import run_flops_benchmark

if TYPE_CHECKING:
    from .flops import FlopsBenchmarkSuite


def __getattr__(name: str) -> object:
    """Resolve the flops suite on first access, reporting a missing extra as install guidance."""
    if name != "FlopsBenchmarkSuite":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    with Capability.FLOPS_BENCHMARKING.required():
        from . import flops

    return flops.FlopsBenchmarkSuite


__all__ = ["FlopsBenchmarkResults", "run_flops_benchmark"]


def __dir__() -> list[Any]:
    return [*__all__, "FlopsBenchmarkSuite"]
