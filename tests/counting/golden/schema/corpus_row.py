"""`CorpusRow` records a probe plus everything the golden test asserts about it.

A probe is a snippet string over the injected `num` — `CountedFloat` for the counted run,
`float` for the plain run — compiled once at import, so the snippet doubles as the row's
test ID and as the expression a failure message shows.

Citations use two prefixes: `rules:<anchor>` names an anchor in `docs/cost_model_rules.md`,
`interp:<slug>` one in `docs/cost_model_interpretations.md`.
"""

import copy
import math
import pickle
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction

# Rules-page anchors.
R_CONTRACT = "rules:the-contract"
R_SCOPE = "rules:what-the-model-prices"
R_PORT = "rules:how-the-port-is-built"
R_RULES = "rules:the-rules"
R_ENDINGS = "rules:where-countedness-ends"
R_RECORDS = "rules:what-a-count-records"

# Interpretation slugs.
I_FMA = "interp:fma-stays-as-written"
I_EXPONENT_CHAIN = "interp:exponent-chain-bound"
I_CLASSIFIERS = "interp:classifiers-price-their-question"
I_EXP10 = "interp:exp10-is-pow"
I_LOG_BASE = "interp:log-constant-base-folds"
I_IDENTITY_FOLDS = "interp:identity-folds-are-sign-exact"
I_RECIPROCAL = "interp:reciprocal-exactness-bound"
I_FMAX_COMP = "interp:fmax-shares-comp-weight"
I_MEASUREMENT = "interp:measurement-fallbacks"
I_FORMULA_FIXED = "interp:formula-price-is-fixed"
I_LOOPS = "interp:loops-do-not-fold"

# Everything a snippet may name besides `num`. Fixed rather than the module's globals, so a
# snippet cannot silently depend on a corpus-internal name.
_SNIPPET_NAMESPACE = {
    "math": math,
    "Decimal": Decimal,
    "Fraction": Fraction,
    "pickle": pickle,
    "copy": copy,
}


@dataclass(frozen=True)
class CorpusRow:
    """One executable counting decision of the reference corpus.

    Args:
        row_id: Frozen decision-row ID; several probes may share one ID when they pin the
            same decision from different angles.
        snippet: The probe's source over `num`; `row_id` + `snippet` form the test ID.
        probe: The compiled snippet (or the hand-written override, where a snippet cannot
            express the probe — see `row`).
        counts: Expected flop counts of one counted execution, keyed by `FlopType.value`,
            zero-count types omitted. The golden test asserts full-dict equality, so an
            absent key asserts that type counts nothing.
        outcome: Expected outcome of the counted run: an exact result type, a tuple of exact
            types for container results, or — for a probe that raises on both runs — the
            exception type (any `BaseException` subclass reads as "raises").
        requires: Availability gate, interpreted by `helpers.runner.gate_reason`; `None` when the
            probe runs everywhere.
        cites: Cost-model citations (`rules:` / `interp:` prefixed) that force the outcome.
        plain_parity: Whether the plain run reproduces the counted run's outcome
            bit-for-bit. Off where the outcome deliberately encodes the type (`repr`), or
            where the operation itself distinguishes the subclass — numpy accepts a plain
            float and rejects `CountedFloat`, and that rejection is what the row pins. The
            plain run still executes and still must count nothing; only the outcome
            comparison is skipped.
        unpatched_parity: Whether that parity survives with `math.*` unpatched (the outside
            regime). Off only where the *unpatched* stdlib computes a different value for a
            float subclass — CPython's `sumprod` reserves its extended-precision path for
            exact `float`s, so for a subclass its cancellation-sensitive results diverge.
    """

    row_id: str
    snippet: str
    probe: Callable[[type], object]
    counts: dict[str, int]
    outcome: type | tuple[type, ...]
    requires: str | None = None
    cites: tuple[str, ...] = field(default=())
    plain_parity: bool = True
    unpatched_parity: bool = True

    @property
    def raises(self) -> type[BaseException] | None:
        """Return the exception type of a raising probe, or None for a returning probe."""
        if isinstance(self.outcome, type) and issubclass(self.outcome, BaseException):
            return self.outcome
        return None

    @property
    def uid(self) -> str:
        """Return the unique test ID of this probe."""
        return f"{self.row_id}:{self.snippet}"


def row(
    row_id: str,
    snippet: str,
    counts: dict[str, int],
    outcome: type | tuple[type, ...],
    *cites: str,
    requires: str | None = None,
    plain_parity: bool = True,
    unpatched_parity: bool = True,
    probe: Callable[[type], object] | None = None,
) -> CorpusRow:
    """Build one corpus row from a table entry.

    `probe` overrides compilation for the rare probe a snippet cannot express (the numpy
    rows, whose import cannot live in the fixed namespace); the snippet still serves as ID.
    """
    return _build_row(row_id, snippet, counts, outcome, cites, requires, plain_parity, unpatched_parity, probe)


def rows(
    row_id: str,
    snippet: str,
    counts: dict[str, int] | Callable[[object], dict[str, int]],
    outcome: type | tuple[type, ...],
    *cites: str,
    requires: str | None = None,
    plain_parity: bool = True,
    unpatched_parity: bool = True,
    **axis: list,
) -> list[CorpusRow]:
    """Expand one family entry into a `CorpusRow` per value of its (single) axis.

    The axis (`n=[1, 2, 5]`) substitutes each value textually into the snippet's `{n}` hole;
    `counts` may then be a callable of the axis value, so a family states its pricing formula
    once — zero-valued counts are dropped, so a formula may reach zero at a boundary value.
    """
    if len(axis) != 1:
        raise ValueError(f"{row_id}: a family takes exactly one axis, got {sorted(axis)}")
    ((name, values),) = axis.items()
    return [
        _build_row(
            row_id,
            snippet.replace("{" + name + "}", str(value)),
            counts(value) if callable(counts) else counts,
            outcome,
            cites,
            requires,
            plain_parity,
            unpatched_parity,
            None,
        )
        for value in values
    ]


def _build_row(
    row_id: str,
    snippet: str,
    counts: dict[str, int],
    outcome: type | tuple[type, ...],
    cites: tuple[str, ...],
    requires: str | None,
    plain_parity: bool,
    unpatched_parity: bool,
    probe: Callable[[type], object] | None,
) -> CorpusRow:
    """Assemble one `CorpusRow`, dropping zero counts and compiling the snippet."""
    return CorpusRow(
        row_id=row_id,
        snippet=snippet,
        probe=probe if probe is not None else _compile_snippet(row_id, snippet),
        counts={flop_type: count for flop_type, count in counts.items() if count},
        outcome=outcome,
        requires=requires,
        cites=cites,
        plain_parity=plain_parity,
        unpatched_parity=unpatched_parity,
    )


def _compile_snippet(row_id: str, snippet: str) -> Callable[[type], object]:
    """Compile a snippet string into the probe callable over `num`."""
    source = f"lambda num: ({snippet})"
    try:
        return eval(compile(source, f"<corpus {row_id}>", "eval"), dict(_SNIPPET_NAMESPACE))  # noqa: S307 -- fixed corpus literals, no user input
    except SyntaxError as exc:
        raise SyntaxError(f"corpus row {row_id}: cannot compile {snippet!r}") from exc
