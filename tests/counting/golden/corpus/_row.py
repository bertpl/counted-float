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
        result: Expected result shape of the counted run: an exact type, or a tuple of exact
            types for container results. `None` iff `raises` is set.
        raises: Exception type the probe raises (on both runs), or `None`.
        requires: Availability gate, interpreted by `_runner.gate_reason`; `None` when the
            probe runs everywhere.
        cites: Cost-model citations (`rules:` / `interp:` prefixed) that force the outcome.
        twin: Whether the plain run must reproduce the counted run's outcome bit-for-bit.
            Off only where the outcome deliberately encodes the type (e.g. `repr`), or where
            the plain twin legitimately diverges (numpy accepts plain floats).
        reinforces: True for redundancy probes beyond the strictly needed one — extra angles
            on the same decision, typically both sides of a value boundary.
    """

    row_id: str
    snippet: str
    probe: Callable[[type], object]
    counts: dict[str, int]
    result: type | tuple[type, ...] | None = None
    raises: type[BaseException] | None = None
    requires: str | None = None
    cites: tuple[str, ...] = field(default=())
    twin: bool = True
    reinforces: bool = False

    @property
    def uid(self) -> str:
        """Return the unique test ID of this probe."""
        return f"{self.row_id}:{self.snippet}"


def row(
    row_id: str,
    snippet: str,
    counts: dict[str, int] | Callable[[object], dict[str, int]],
    result: type | tuple[type, ...] | None = None,
    *cites: str,
    raises: type[BaseException] | None = None,
    requires: str | None = None,
    twin: bool = True,
    reinforces: bool = False,
    probe: Callable[[type], object] | None = None,
    **axis: list,
) -> list[CorpusRow]:
    """Expand one corpus entry into its `CorpusRow`s — one per value of the (single) axis.

    An axis (`n=[1, 2, 5]`) substitutes each value textually into the snippet's `{n}` hole
    and expands to one row per value; `counts` may then be a callable of the axis value, so a
    family states its pricing formula once. Snippets without an axis are used verbatim, so
    literal braces are only off-limits in axis snippets.

    `probe` overrides compilation for the rare probe a snippet cannot express (the numpy
    rows, whose import cannot live in the fixed namespace); the snippet still serves as ID.
    """
    if len(axis) > 1:
        raise ValueError(f"{row_id}: at most one axis per row, got {sorted(axis)}")

    def build(filled_snippet: str, expected: dict[str, int]) -> CorpusRow:
        compiled = probe if probe is not None else _compile_snippet(row_id, filled_snippet)
        return CorpusRow(
            row_id=row_id,
            snippet=filled_snippet,
            probe=compiled,
            counts=expected,
            result=result,
            raises=raises,
            requires=requires,
            cites=cites,
            twin=twin,
            reinforces=reinforces,
        )

    if not axis:
        assert not callable(counts), f"{row_id}: callable counts need an axis"
        return [build(snippet, counts)]
    ((name, values),) = axis.items()
    return [
        build(snippet.replace("{" + name + "}", str(value)), counts(value) if callable(counts) else counts)
        for value in values
    ]


def flat(groups: list[list[CorpusRow]]) -> list[CorpusRow]:
    """Concatenate the row groups a section's table produces."""
    return [corpus_row for group in groups for corpus_row in group]


def _compile_snippet(row_id: str, snippet: str) -> Callable[[type], object]:
    """Compile a snippet string into the probe callable over `num`."""
    source = f"lambda num: ({snippet})"
    try:
        return eval(compile(source, f"<corpus {row_id}>", "eval"), dict(_SNIPPET_NAMESPACE))  # noqa: S307 -- fixed corpus literals, no user input
    except SyntaxError as exc:
        raise SyntaxError(f"corpus row {row_id}: cannot compile {snippet!r}") from exc
