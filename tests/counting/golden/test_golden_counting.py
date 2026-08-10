"""One parametrized test drives the whole corpus, asserting each row from every angle.

The dimensions are the corpus rows, the context regime, and the repetition count:

- **counts** — exact full-dict equality, scaled linearly by the repetition count in one
  context, so a counter that accumulates wrongly fails visibly; the paused regime expects
  zero counts at every repetition, the outside regime has no counter to read;
- **result shape** — exact result types under counting and paused (types survive pausing);
  outside, `math.*` is unpatched, so results legitimately go plain and only values compare;
- **the plain run** — the identical snippet on plain floats counts nothing on every row, and
  (where `plain_parity` holds) produces a bit-identical outcome, so counting never changes a
  value.

"""

import pytest

from counted_float import CountedFloat

from .corpus import ROWS, CorpusRow
from .helpers import REGIMES, assert_result_shape, gate_reason, run_probe

_REPETITIONS = (1, 2, 5)


@pytest.mark.parametrize("reps", _REPETITIONS)
@pytest.mark.parametrize("regime", REGIMES)
@pytest.mark.parametrize("row", ROWS, ids=[row.uid for row in ROWS])
def test_golden_counting(row: CorpusRow, regime: str, reps: int) -> None:
    """One corpus row holds under one regime: counts, result shape, and the plain run."""
    if reason := gate_reason(row.requires):
        pytest.skip(reason)
    if regime == "outside" and not (row.plain_parity and row.unpatched_parity):
        pytest.skip("row's outcome legitimately differs between counted and plain")

    # --- counted run ------------------
    run = run_probe(row, CountedFloat, reps, regime)
    if row.raises is not None:
        for outcome in run.outcomes:
            assert outcome == ("raises", row.raises), f"{row.uid}: expected {row.raises.__name__}, got {outcome}"
    assert len(set(run.outcomes)) == 1, f"{row.uid}: outcome varies across repetitions"

    # --- counts and result shape ------
    if regime in ("counting", "paused"):
        expected = {flop_type: count * reps for flop_type, count in row.counts.items()} if regime == "counting" else {}
        assert run.counts == expected, f"{row.uid} [{regime}]: counts at {reps}x are {run.counts}, expected {expected}"
        if row.raises is None:
            assert_result_shape(run.raw_last, row)

    # --- the plain run ----------------
    plain = run_probe(row, float, 1, regime)
    assert plain.counts == {}, f"{row.uid} [{regime}]: plain run counted {plain.counts}"
    if row.plain_parity:
        assert plain.outcomes[0] == run.outcomes[0], (
            f"{row.uid} [{regime}]: plain outcome {plain.outcomes[0]} differs from counted {run.outcomes[0]}"
        )
