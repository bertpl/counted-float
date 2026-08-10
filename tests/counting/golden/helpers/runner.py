"""The runner executes corpus probes and reduces their outcomes to a comparable form.

A probe runs under one of three context regimes — `counting` (a fresh `FlopCountingContext`),
`paused` (the same, inside `PauseFlopCounting`), or `outside` (no context at all). Float-valued
parts of an outcome compare by bit pattern (so `-0.0` vs `+0.0` and NaN payloads are visible),
everything else by type and value, and a raising probe by its exception type.
"""

import importlib.util
import math
import struct
from contextlib import nullcontext
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from counted_float import FlopCountingContext, PauseFlopCounting
from tests.counting.golden.schema import CorpusRow

REGIMES = ("counting", "paused", "outside")


def gate_reason(requires: str | None) -> str | None:
    """Return why a row cannot run here, or None when its requirement is met."""
    if requires is None:
        return None
    if requires == "numpy":
        return None if importlib.util.find_spec("numpy") else "requires numpy"
    if requires == "from_number":
        return None if hasattr(float, "from_number") else "requires float.from_number (3.14+)"
    if requires == "exact-log-e":
        # The log-base identity folds depend on the runtime libm value, so a libm computing
        # log(e) or log(1/e) inexactly makes the fold legitimately not fire.
        exact = math.log(math.e) == 1.0 and math.log(1.0 / math.e) == -1.0
        return None if exact else "requires a libm where log(e) == 1.0 and log(1/e) == -1.0"
    return None if hasattr(math, requires) else f"requires math.{requires}"


@dataclass(frozen=True)
class ProbeRun:
    """One repeated probe run's aggregated results.

    `raw_last` is the unreduced result of the final execution — what result-shape assertions
    inspect — and `None` when the probe raised.
    """

    counts: dict[str, int]
    outcomes: list[object]
    raw_last: object


def run_probe(row: CorpusRow, number_type: type, reps: int, regime: str = "counting") -> ProbeRun:
    """Execute a row's probe `reps` times under one context regime.

    The counting regime asserts its context opens at zero counts, so state leaking from a
    previous probe is caught before it can hide in this row's counts. The outside regime has
    no context to read, so its counts are empty by construction.
    """
    if regime == "outside":
        executions = [_execute(row, number_type) for _ in range(reps)]
        return ProbeRun(counts={}, outcomes=[comparable for _, comparable in executions], raw_last=executions[-1][0])
    with FlopCountingContext() as ctx:
        assert not _nonzero_counts(ctx), "context must open at zero counts"
        with PauseFlopCounting() if regime == "paused" else nullcontext():
            executions = [_execute(row, number_type) for _ in range(reps)]
    return ProbeRun(
        counts=_nonzero_counts(ctx), outcomes=[comparable for _, comparable in executions], raw_last=executions[-1][0]
    )


def comparable_outcome(value: object) -> object:
    """Reduce a probe result to a hashable form where equality means bit-level identity.

    Floats (`CountedFloat` included) reduce to their IEEE 754 bit pattern, so signed zeros
    and NaNs compare exactly; containers reduce per element; `complex` per component. The
    remaining result types the corpus produces (`bool`, `int`, `str`, `Decimal`, `Fraction`)
    compare by ordinary equality, with `bool` tagged so `True` never equals `1.0`'s bits.
    """
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, float):
        return ("float-bits", struct.pack("<d", value))
    if isinstance(value, complex):
        return ("complex", comparable_outcome(value.real), comparable_outcome(value.imag))
    if isinstance(value, (tuple, list)):
        return tuple(comparable_outcome(v) for v in value)
    if isinstance(value, (int, str, Decimal, Fraction)):
        return value
    raise TypeError(f"corpus probe produced an uncomparable {type(value).__name__}")


def assert_result_shape(raw: object, row: CorpusRow) -> None:
    """Assert one raw probe result matches the row's expected result shape exactly.

    Exact `type(...) is` checks on purpose: a `CountedFloat` result asserted as `float`
    (or vice versa) is precisely the countedness defect the corpus exists to catch.
    """
    spec = row.outcome
    if isinstance(spec, tuple):
        assert isinstance(raw, tuple), f"{row.uid}: expected a tuple result, got {type(raw).__name__}"
        assert len(raw) == len(spec), f"{row.uid}: expected {len(spec)} elements, got {len(raw)}"
        for element, element_type in zip(raw, spec, strict=True):
            assert type(element) is element_type, (
                f"{row.uid}: element {element!r} is {type(element).__name__}, expected {element_type.__name__}"
            )
    else:
        assert type(raw) is spec, f"{row.uid}: result {raw!r} is {type(raw).__name__}, expected {spec.__name__}"


def _execute(row: CorpusRow, number_type: type) -> tuple[object, object]:
    """Run the probe once, returning the raw result paired with its comparable form.

    A raising probe yields `(None, ("raises", <exception type>))` — the exception type is
    the outcome.
    """
    try:
        raw = row.probe(number_type)
        return raw, comparable_outcome(raw)
    except Exception as exc:  # noqa: BLE001 -- the exception type is the outcome
        return None, ("raises", type(exc))


def _nonzero_counts(ctx: FlopCountingContext) -> dict[str, int]:
    """Extract the context's nonzero flop counts keyed by flop-type value."""
    return {k.value: v for k, v in ctx.flop_counts().as_dict().items() if v}
