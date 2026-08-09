"""Schema of one golden-corpus row: a probe plus everything the golden test asserts about it.

Each row is one counting decision of the cost model, executable: the probe runs the snippet
with an injected number type (`CountedFloat` for the counted run, `float` for the plain twin),
and the row states the expected counts, the expected result shape, and the cost-model text
that forces the outcome.

Citations use two prefixes, resolved against the docs pages by the corpus meta-tests:
`rules:<anchor>` points into `docs/cost_model_rules.md`, `interp:<slug>` into
`docs/cost_model_interpretations.md`.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

# --- rules-page anchors -----------------------
R_CONTRACT = "rules:the-contract"
R_SCOPE = "rules:what-the-model-prices"
R_PORT = "rules:how-the-port-is-built"
R_RULES = "rules:the-rules"
R_ENDINGS = "rules:where-countedness-ends"
R_RECORDS = "rules:what-a-count-records"

# --- interpretation slugs ---------------------
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


@dataclass(frozen=True)
class GoldenRow:
    """One executable counting decision of the reference corpus.

    Args:
        row_id: Frozen decision-row ID (`A1`..`D15`); several probes may share one ID when
            they pin the same decision from different angles.
        label: Short unique probe description; `row_id` + `label` form the test ID.
        probe: Runs the snippet once. Receives the number type to build values with —
            `CountedFloat` for the counted run, `float` for the plain twin — so both runs
            execute the identical snippet.
        counts: Expected flop counts of one counted execution, keyed by `FlopType.value`,
            zero-count types omitted. The golden test asserts full-dict equality, so an
            absent key asserts that type counts nothing.
        result: Expected result shape of the counted run: an exact type, or a tuple of exact
            types for container results. `None` iff `raises` is set.
        raises: Exception type the probe raises (on both runs), or `None`.
        requires: Availability gate: a `math` attribute name, `"from_number"`, or `"numpy"`;
            `None` when the probe runs everywhere.
        cites: Cost-model citations (`rules:` / `interp:` prefixed) that force the outcome.
        twin: Whether the plain run must reproduce the counted run's outcome bit-for-bit.
            Off only where the outcome deliberately encodes the type (e.g. `repr`), or where
            the plain twin legitimately diverges (numpy accepts plain floats).
        reinforces: True for redundancy probes beyond the strictly needed one — extra angles
            on the same decision, typically both sides of a value boundary.
    """

    row_id: str
    label: str
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
        return f"{self.row_id}:{self.label}"
