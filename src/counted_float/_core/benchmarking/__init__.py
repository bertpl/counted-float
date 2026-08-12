"""The flops benchmark suite: what this package means, gated end to end.

Everything under `flops` needs the benchmarking extra, and `run_flops_benchmark` is the only place
that reaches it — behind the guard, inside the call. So this module stays importable without the
extra, which it has to be: the public package re-exports through it on installs carrying no extras
at all, and a guard has to be reachable to be able to report anything.

FlopsBenchmarkResults is a plain model rather than part of the suite, so it comes straight from its
own package and stays eagerly available: reading a stored result needs no extra.
"""

from counted_float._core.models import FlopsBenchmarkResults

from .runner import run_flops_benchmark

__all__ = ["FlopsBenchmarkResults", "run_flops_benchmark"]
