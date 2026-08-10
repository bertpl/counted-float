"""Section A holds the cross-cutting regime decisions.

Snippets run over the injected `num` — `CountedFloat` counted, plain `float` for the twin run.

Rows A5 (outside any context) and A6 (paused) are not probe rows: the golden test runs every
row under all three context regimes, so those two decisions are the regime dimension itself.
"""

from counted_float import CountedFloat

from ._row import (
    I_CLASSIFIERS,
    R_CONTRACT,
    R_ENDINGS,
    R_PORT,
    R_RECORDS,
    R_SCOPE,
    CorpusRow,
    flat,
    row,
)

CF = CountedFloat


def _numpy_probe(expression):
    """Wrap a numpy-dependent probe so the corpus imports without numpy installed."""

    def probe(number_type: type) -> object:
        import numpy as np

        return expression(number_type, np)

    return probe


# The numpy probes are the one place a snippet cannot express the probe (the import cannot
# live in the fixed snippet namespace); each row carries a hand-written callable instead, with
# its snippet serving as the test ID.
_NUMPY_MUL_ARRAY = _numpy_probe(lambda num, np: num(2.0) * np.array([1.0]))
_NUMPY_MUL_FLOAT32 = _numpy_probe(lambda num, np: num(2.0) * np.float32(1.0))
_NUMPY_FLOAT64_BOTH_SIDES = _numpy_probe(lambda num, np: (num(1.0) + np.float64(2.0), np.float64(2.0) + num(1.0)))


# fmt: off
ROWS: list[CorpusRow] = flat([
    row("A1",  "math.sqrt(2.0)",                                   {},                       float,        R_CONTRACT),
    row("A1",  "math.sqrt(3)",                                     {},                       float,        R_CONTRACT),
    row("A2",  "math.sqrt(num(2.0))",                              {"SQRT": 1},              CF,           R_PORT),
    row("A2",  "math.fmax(num(math.nan), 1.0)",                    {"COMP": 1},              CF,           R_PORT, requires="fmax"),
    row("A3",  "(round(num(2.7)), num(1.0) < 2.0)",                {"COMP": 1, "F2I": 1},    (int, bool),  R_ENDINGS),
    row("A4",  "math.sqrt(num(-1.0))",                             {},                       None,         R_RECORDS, raises=ValueError),
    row("A4",  "math.log(num(-1.0))",                              {},                       None,         R_RECORDS, raises=ValueError),
    row("A4",  "math.fmod(num(1.0), 0.0)",                         {},                       None,         R_RECORDS, raises=ValueError),
    row("A4",  "num(1.0) / 0.0",                                   {},                       None,         R_RECORDS, raises=ZeroDivisionError),
    row("A4",  "num(1.0) % 0.0",                                   {},                       None,         R_RECORDS, raises=ZeroDivisionError),
    row("A4",  "num(10**400)",                                     {},                       None,         R_RECORDS, raises=OverflowError),
    row("A4",  "math.prod([num(2.0), num(3.0), None])",            {},                       None,         R_RECORDS, raises=TypeError),
    row("A4",  "math.prod([num(2.0), None])",                      {},                       None,         R_RECORDS, raises=TypeError),
    row("A7",  "num(1.0) + 2",                                     {"ADD": 1},               CF,           R_CONTRACT),
    row("A7",  "num(1.0) + True",                                  {"ADD": 1},               CF,           R_CONTRACT),
    row("A8",  "num(5)",                                           {"I2F": 1},               CF,           R_SCOPE),
    row("A8",  "num(True)",                                        {"I2F": 1},               CF,           R_SCOPE),
    row("A8",  "num.from_number(5)",                               {"I2F": 1},               CF,           R_SCOPE, requires="from_number"),
    row("A9",  "num(1.0) + Decimal('1.5')",                        {},                       None,         R_SCOPE, raises=TypeError),
    row("A10", "(num(1.5) == Decimal('1.5'), num(1.5) < Decimal('2.5'))", {},                (bool, bool), R_SCOPE),
    row("A11", "num(1.0) + Fraction(1, 2)",                        {},                       float,        R_ENDINGS),
    row("A12", "Fraction(1, 2) + num(1.0)",                        {"ADD": 1},               CF,           R_RECORDS),
    row("A13", "num(0.3) < Fraction(1, 2)",                        {"ABS": 1, "COMP": 2},    bool,         R_RECORDS, I_CLASSIFIERS),
    row("A15", "divmod(num(7.0), 3.0)",                            {"DIV": 1, "MUL": 1, "RND": 1, "SUB": 1}, (CF, CF), R_PORT),
    row("A16", "(num(1.0) + 1j, num(1.0) * (2 + 3j))",             {},                       (complex, complex), R_ENDINGS),
    row("A17", "(num(1.0) == 1j, num(1.0) == (1 + 0j))",           {},                       (bool, bool), R_ENDINGS),
    row("A17", "num(1.0) < 1j",                                    {},                       None,         R_ENDINGS, raises=TypeError),
    row("A18", "math.comb(num(4.0), 2)",                           {},                       None,         R_SCOPE, raises=TypeError),
    row("A18", "math.factorial(num(4.0))",                         {},                       None,         R_SCOPE, raises=TypeError),
    row("A18", "math.gcd(num(4.0), 2)",                            {},                       None,         R_SCOPE, raises=TypeError),
    row("A18", "math.isqrt(num(4.0))",                             {},                       None,         R_SCOPE, raises=TypeError),
    row("A18", "math.lcm(num(4.0), 2)",                            {},                       None,         R_SCOPE, raises=TypeError),
    row("A14", "num(2.0) * np.array([1.0])",                       {},                       None,         R_SCOPE, raises=TypeError, requires="numpy", plain_parity=False, probe=_NUMPY_MUL_ARRAY),
    row("A14", "num(2.0) * np.float32(1.0)",                       {},                       None,         R_SCOPE, raises=TypeError, requires="numpy", plain_parity=False, probe=_NUMPY_MUL_FLOAT32),
    row("A14", "(num(1.0) + np.float64(2.0), np.float64(2.0) + num(1.0))", {"ADD": 2},       (CF, CF),     R_SCOPE, requires="numpy", plain_parity=False, probe=_NUMPY_FLOAT64_BOTH_SIDES),
    row("A18", "math.perm(num(4.0), 2)",                           {},                       None,         R_SCOPE, raises=TypeError),
])
# fmt: on
