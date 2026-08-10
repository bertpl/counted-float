"""The corpus: every counting decision as a table of rows, grouped into four section files.

- `cross_cutting.py` (A) — rules that apply to every operation: contagion, plain-operand
  delegation, the compute-before-count contract on a raise, integer constants, and mixed-type
  interop (`Decimal`, `Fraction`, `complex`, numpy).
- `uniform_operations.py` (B) — operations with one fixed tally per call: the transcendentals,
  the classifiers, `isclose`, `fsum`.
- `value_dependent.py` (C) — operations whose tally depends on the operand value: the identity
  and reciprocal folds, the exponent and log-base ladders, the floored-division family, and the
  arity-scaled and sequence calls.
- `float_surface.py` (D) — the float surface and the exits where countedness ends: `repr`, hex,
  conversions out of the float domain, `int`/`float`/`bool`.

Row IDs (`A1`, `B3`, …) are stable labels grouping a decision's probes; the sequence is
contiguous within each section and carries no meaning beyond the grouping.
"""

from tests.counting.golden.schema import CorpusRow

from .cross_cutting import ROWS as _CROSS_CUTTING_ROWS
from .float_surface import ROWS as _FLOAT_SURFACE_ROWS
from .uniform_operations import ROWS as _UNIFORM_ROWS
from .value_dependent import ROWS as _VALUE_DEPENDENT_ROWS

ROWS: list[CorpusRow] = [*_CROSS_CUTTING_ROWS, *_UNIFORM_ROWS, *_VALUE_DEPENDENT_ROWS, *_FLOAT_SURFACE_ROWS]

_snippets = [corpus_row.snippet for corpus_row in ROWS]
assert len(_snippets) == len(set(_snippets)), "corpus snippets must be unique across all sections"
