"""One parametrized test drives the whole corpus, asserting each row from every angle.

- **counts** — exact full-dict equality at one repetition, and linear scaling at each
  higher count in `_REPETITIONS`, so a counter that accumulates wrongly fails visibly;
- **result shape** — exact result types, on every repetition;
- **the plain twin** — the identical snippet on plain floats counts nothing and produces a
  bit-identical outcome, so counting never changes a value and a snippet with no counted
  operand stays plain, on every row.

Rows A5 and A6 are covered by `test_outside_context_regime` and `test_paused_regime`; see
`_corpus_regimes` for why they sit outside the shared runner.
"""

import math

import pytest

from counted_float import CountedFloat, FlopCountingContext, PauseFlopCounting

from ._corpus import ROWS
from ._row import GoldenRow
from ._runner import assert_result_shape, gate_reason, run_probe, scaled_counts

_REPETITIONS = (1, 2, 5)


@pytest.mark.parametrize("row", ROWS, ids=[row.uid for row in ROWS])
def test_golden_counting(row: GoldenRow) -> None:
    """One corpus row holds: counts, linear scaling, result shape, and the plain twin."""
    if reason := gate_reason(row.requires):
        pytest.skip(reason)

    # --- counted runs per repetition count ------
    baseline = None
    for reps in _REPETITIONS:
        run = run_probe(row, CountedFloat, reps)
        assert run.counts == scaled_counts(row.counts, reps), (
            f"{row.uid}: counts at {reps}x are {run.counts}, expected {scaled_counts(row.counts, reps)}"
        )
        for outcome in run.outcomes:
            if row.raises is not None:
                assert outcome == ("raises", row.raises), f"{row.uid}: expected {row.raises.__name__}, got {outcome}"
        assert len(set(map(repr, run.outcomes))) == 1, f"{row.uid}: outcome varies across repetitions"
        if reps == 1:
            baseline = run.outcomes[0]

    # --- result shape (non-raising rows) --------
    if row.raises is None:
        raw = _raw_result(row)
        assert_result_shape(raw, row)

    # --- the plain twin -------------------------
    if row.twin:
        twin = run_probe(row, float, 1)
        assert twin.counts == {}, f"{row.uid}: plain twin counted {twin.counts}"
        assert twin.outcomes[0] == baseline, (
            f"{row.uid}: plain twin outcome {twin.outcomes[0]} differs from counted {baseline}"
        )


def _raw_result(row: GoldenRow) -> object:
    """Execute a non-raising row once and return the raw (uncompared) result."""
    with FlopCountingContext():
        return row.probe(CountedFloat)


# ==================================================================================================
#  The two regimes outside the runner's model
# ==================================================================================================
def test_outside_context_regime() -> None:
    """Row A5: without a context, math.* is unpatched and only operators preserve the type."""
    # --- act --------------------------
    via_math = math.sqrt(CountedFloat(4.0))
    via_operator = CountedFloat(2.0) + 1.0

    # --- assert -----------------------
    assert type(via_math) is float
    assert type(via_operator) is CountedFloat


def test_paused_regime() -> None:
    """Row A6: paused keeps patches installed and types counted while suppressing counts."""
    # --- arrange / act ----------------
    with FlopCountingContext() as ctx, PauseFlopCounting():
        via_math = math.sqrt(CountedFloat(4.0))
        via_operator = CountedFloat(2.0) + 1.0

    # --- assert -----------------------
    assert type(via_math) is CountedFloat
    assert type(via_operator) is CountedFloat
    assert not any(ctx.flop_counts().as_dict().values())
