"""The corpus vocabulary: the row type, the table factories, and the cost-model citations.

Both the corpus data (`corpus/`) and the test machinery (`helpers/`) depend on this package,
so it holds no dependency on either — the shared foundation the golden suite is built from.
"""

from .corpus_row import (
    I_CLASSIFIERS,
    I_EXP10,
    I_EXPONENT_CHAIN,
    I_FMA,
    I_FMAX_COMP,
    I_FORMULA_FIXED,
    I_IDENTITY_FOLDS,
    I_LOG_BASE,
    I_LOOPS,
    I_MEASUREMENT,
    I_RECIPROCAL,
    R_CONTRACT,
    R_ENDINGS,
    R_PORT,
    R_RECORDS,
    R_RULES,
    R_SCOPE,
    CorpusRow,
    row,
    rows,
)

__all__ = [
    "I_CLASSIFIERS",
    "I_EXP10",
    "I_EXPONENT_CHAIN",
    "I_FMA",
    "I_FMAX_COMP",
    "I_FORMULA_FIXED",
    "I_IDENTITY_FOLDS",
    "I_LOG_BASE",
    "I_LOOPS",
    "I_MEASUREMENT",
    "I_RECIPROCAL",
    "R_CONTRACT",
    "R_ENDINGS",
    "R_PORT",
    "R_RECORDS",
    "R_RULES",
    "R_SCOPE",
    "CorpusRow",
    "row",
    "rows",
]
