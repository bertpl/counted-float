"""This module aggregates all corpus sections and asserts probe IDs are unique."""

from ._corpus_regimes import ROWS as _REGIME_ROWS
from ._corpus_subcases import ROWS as _SUBCASE_ROWS
from ._corpus_surface import ROWS as _SURFACE_ROWS
from ._corpus_uniform import ROWS as _UNIFORM_ROWS
from ._row import GoldenRow

ROWS: list[GoldenRow] = [*_REGIME_ROWS, *_UNIFORM_ROWS, *_SUBCASE_ROWS, *_SURFACE_ROWS]

_uids = [row.uid for row in ROWS]
assert len(_uids) == len(set(_uids)), "corpus probe IDs must be unique"
