"""This package aggregates all corpus sections and asserts probe IDs are unique."""

from tests.counting.golden.schema import CorpusRow

from .regimes import ROWS as _REGIME_ROWS
from .subcases import ROWS as _SUBCASE_ROWS
from .surface import ROWS as _SURFACE_ROWS
from .uniform import ROWS as _UNIFORM_ROWS

ROWS: list[CorpusRow] = [*_REGIME_ROWS, *_UNIFORM_ROWS, *_SUBCASE_ROWS, *_SURFACE_ROWS]

_uids = [corpus_row.uid for corpus_row in ROWS]
assert len(_uids) == len(set(_uids)), "corpus probe IDs must be unique"
