"""This package aggregates all corpus sections and asserts probe IDs are unique."""

from ._regimes import ROWS as _REGIME_ROWS
from ._row import CorpusRow
from ._subcases import ROWS as _SUBCASE_ROWS
from ._surface import ROWS as _SURFACE_ROWS
from ._uniform import ROWS as _UNIFORM_ROWS

ROWS: list[CorpusRow] = [*_REGIME_ROWS, *_UNIFORM_ROWS, *_SUBCASE_ROWS, *_SURFACE_ROWS]

_uids = [corpus_row.uid for corpus_row in ROWS]
assert len(_uids) == len(set(_uids)), "corpus probe IDs must be unique"
