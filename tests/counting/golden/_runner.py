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

from counted_float import CountedFloat, FlopCountingContext, PauseFlopCounting

from .corpus import CorpusRow

REGIMES = ("counting", "paused", "outside")


def gate_reason(requires: str | None) -> str | None:
    """Return why a row cannot run here, or None when its requirement is met."""
    if requires is None:
        return None
    if requires == "numpy":
        return None if importlib.util.find_spec("numpy") else "requires numpy"
    if requires == "from_number":
        return None if hasattr(float, "from_number") else "requires float.from_number (3.14+)"
    return None if hasattr(math, requires) else f"requires math.{requires}"


@dataclass(frozen=True)
class ProbeRun:
    """A ProbeRun holds the counts and per-execution outcomes of one repeated probe run."""

    counts: dict[str, int]
    outcomes: list[object]


def run_probe(row: CorpusRow, number_type: type, reps: int, regime: str = "counting") -> ProbeRun:
    """Execute a row's probe `reps` times under one context regime.

    The counting regime asserts its context opens at zero counts, so state leaking from a
    previous probe is caught before it can hide in this row's counts. The outside regime has
    no context to read, so its counts are empty by construction.
    """
    if regime == "outside":
        return ProbeRun(counts={}, outcomes=[_execute(row, number_type) for _ in range(reps)])
    with FlopCountingContext() as ctx:
        assert not _nonzero_counts(ctx), "context must open at zero counts"
        with PauseFlopCounting() if regime == "paused" else nullcontext():
            outcomes = [_execute(row, number_type) for _ in range(reps)]
    return ProbeRun(counts=_nonzero_counts(ctx), outcomes=outcomes)


def raw_result(row: CorpusRow, regime: str = "counting") -> object:
    """Execute a non-raising row once and return the raw (uncompared) result."""
    with FlopCountingContext(), PauseFlopCounting() if regime == "paused" else nullcontext():
        return row.probe(CountedFloat)


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
    spec = row.result
    if isinstance(spec, tuple):
        assert isinstance(raw, tuple), f"{row.uid}: expected a tuple result, got {type(raw).__name__}"
        assert len(raw) == len(spec), f"{row.uid}: expected {len(spec)} elements, got {len(raw)}"
        for element, element_type in zip(raw, spec, strict=True):
            assert type(element) is element_type, (
                f"{row.uid}: element {element!r} is {type(element).__name__}, expected {element_type.__name__}"
            )
    else:
        assert type(raw) is spec, f"{row.uid}: result {raw!r} is {type(raw).__name__}, expected {spec.__name__}"


def scaled_counts(counts: dict[str, int], reps: int) -> dict[str, int]:
    """Return the expected counts of `reps` executions: each per-execution count times reps."""
    return {flop_type: count * reps for flop_type, count in counts.items()}


def _execute(row: CorpusRow, number_type: type) -> object:
    """Run the probe once, reducing its result — or its exception type — to a comparable form."""
    try:
        return comparable_outcome(row.probe(number_type))
    except Exception as exc:  # noqa: BLE001 -- the exception type is the outcome
        return ("raises", type(exc))


def _nonzero_counts(ctx: FlopCountingContext) -> dict[str, int]:
    """Extract the context's nonzero flop counts keyed by flop-type value."""
    return {k.value: v for k, v in ctx.flop_counts().as_dict().items() if v}
