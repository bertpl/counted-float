"""Coverage is measured by execution: an instrumented corpus run reports the operations it reached."""

import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field

from counted_float import CountedFloat, FlopCountingContext
from counted_float._core.counting import math_patching
from tests.counting.golden.corpus import ROWS

from .runner import gate_reason

# Each entry names a dunder no corpus probe can reach, with the reason it cannot. The check
# excludes by name rather than working from an inclusion list: an operation added to
# `CountedFloat` is in scope by default, and staying out costs an entry here.
_UNREACHABLE_DUNDERS = {
    # `__init_subclass__` raises at class-definition time, so no probe can call it from inside
    # a running test.
    "__init_subclass__",
}


@dataclass
class CorpusCoverage:
    """A CorpusCoverage records the operations one full corpus run reached."""

    math_names: set[str] = field(default_factory=set)
    dunders: set[str] = field(default_factory=set)


def record_corpus_coverage() -> CorpusCoverage:
    """Run every runnable corpus row once and return the operations the run reached.

    Rows whose availability gate is unmet are skipped, so on an interpreter lacking an
    operation the corresponding names are absent from both the covered set and the expected set.
    """
    coverage = CorpusCoverage()
    with FlopCountingContext(), _recording(coverage):
        for row in ROWS:
            if gate_reason(row.requires):
                continue
            # A raising row still reached the operation it pins; the exception itself is the
            # golden test's business, not this run's.
            with suppress(Exception):
                row.probe(CountedFloat)
    return coverage


def patched_math_names() -> set[str]:
    """Return the `math` names that carry a counting replacement on this interpreter."""
    return set(math_patching._PATCHES)


def reachable_dunders() -> set[str]:
    """Return the `CountedFloat` dunders a corpus probe can reach."""
    own = {name for name, value in vars(CountedFloat).items() if name.startswith("__") and callable(value)}
    return own - _UNREACHABLE_DUNDERS


@contextmanager
def _recording(coverage: CorpusCoverage) -> Iterator[None]:
    """Wrap every counted operation in a recorder for the duration of the block.

    Enter inside an active `FlopCountingContext`: the `math` names are wrapped over the
    counting replacements the context installed, so unwrapping restores the patch rather
    than the stdlib original.
    """
    original_math = {name: getattr(math, name) for name in patched_math_names()}
    original_dunders = {name: getattr(CountedFloat, name) for name in reachable_dunders()}
    try:
        for name, original in original_math.items():
            setattr(math, name, _math_recorder(name, original, coverage))
        for name, original in original_dunders.items():
            setattr(CountedFloat, name, _dunder_recorder(name, original, coverage))
        yield
    finally:
        for name, original in original_math.items():
            setattr(math, name, original)
        for name, original in original_dunders.items():
            setattr(CountedFloat, name, original)


def _math_recorder(name: str, original: Callable[..., object], coverage: CorpusCoverage) -> Callable[..., object]:
    """Return a stand-in for one patched `math` name that records the call and delegates."""

    def recorder(*args: object, **kwargs: object) -> object:
        coverage.math_names.add(name)
        return original(*args, **kwargs)

    return recorder


def _dunder_recorder(name: str, original: Callable[..., object], coverage: CorpusCoverage) -> Callable[..., object]:
    """Return a stand-in for one `CountedFloat` dunder that records the call and delegates."""

    def recorder(*args: object, **kwargs: object) -> object:
        coverage.dunders.add(name)
        return original(*args, **kwargs)

    return recorder
