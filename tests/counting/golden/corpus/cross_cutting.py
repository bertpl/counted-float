"""Section A holds the cross-cutting regime decisions — rules that apply to every operation.

Snippets run over the injected `num` — `CountedFloat` counted, plain `float` for the twin run.
"""

from counted_float import CountedFloat
from tests.counting.golden.schema import (
    I_CLASSIFIERS,
    I_LOOPS,
    R_CONTRACT,
    R_ENDINGS,
    R_PORT,
    R_RECORDS,
    R_RULES,
    R_SCOPE,
    CorpusRow,
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
_NUMPY_FLOAT64_LEFT = _numpy_probe(lambda num, np: num(1.0) + np.float64(2.0))
_NUMPY_FLOAT64_RIGHT = _numpy_probe(lambda num, np: np.float64(2.0) + num(1.0))


# fmt: off
ROWS: list[CorpusRow] = [
    row("A1",  "math.sqrt(2.0)",                                   {},                       float,        R_CONTRACT),
    row("A1",  "math.sqrt(3)",                                     {},                       float,        R_CONTRACT),
    row("A2",  "math.fmax(num(math.nan), 1.0)",                    {"COMP": 1},              CF,           R_PORT, requires="fmax"),
    row("A4",  "math.sqrt(num(-1.0))",                             {},                       ValueError,   R_RECORDS),
    row("A4",  "math.log(num(-1.0))",                              {},                       ValueError,   R_RECORDS),
    row("A4",  "math.fmod(num(1.0), 0.0)",                         {},                       ValueError,   R_RECORDS),
    row("A4",  "num(1.0) / 0.0",                                   {},                       ZeroDivisionError, R_RECORDS),
    row("A4",  "num(1.0) % 0.0",                                   {},                       ZeroDivisionError, R_RECORDS),
    row("A4",  "num(10**400)",                                     {},                       OverflowError, R_RECORDS),
    row("A4",  "math.prod([num(2.0), num(3.0), None])",            {},                       TypeError,    R_RECORDS, I_LOOPS),
    row("A4",  "math.prod([num(2.0), None])",                      {},                       TypeError,    R_RECORDS, I_LOOPS),
    row("A5",  "num(1.0) + 2",                                     {"ADD": 1},               CF,           R_CONTRACT),
    row("A5",  "num(1.0) + True",                                  {"ADD": 1},               CF,           R_CONTRACT),
    row("A6",  "num(True)",                                        {"I2F": 1},               CF,           R_SCOPE),
    row("A6",  "num.from_number(5)",                               {"I2F": 1},               CF,           R_SCOPE, requires="from_number"),
    row("A7",  "num(1.0) + Decimal('1.5')",                        {},                       TypeError,    R_SCOPE),
    row("A8", "num(1.5) == Decimal('1.5')",                        {},                       bool,         R_SCOPE, R_RECORDS),
    row("A8", "num(1.5) < Decimal('2.5')",                         {},                       bool,         R_SCOPE, R_RECORDS),
    row("A9", "num(1.0) + Fraction(1, 2)",                         {},                       float,        R_ENDINGS),
    row("A10", "Fraction(1, 2) + num(1.0)",                        {"ADD": 1},               CF,           R_RECORDS),
    row("A11", "num(0.3) < Fraction(1, 2)",                        {"ABS": 1, "COMP": 2},    bool,         R_RECORDS, I_CLASSIFIERS),
    row("A14", "num(1.0) + 1j",                                    {},                       complex,      R_ENDINGS),
    row("A14", "num(1.0) * (2 + 3j)",                              {},                       complex,      R_ENDINGS),
    row("A15", "num(1.0) == 1j",                                   {},                       bool,         R_ENDINGS),
    row("A15", "num(1.0) == (1 + 0j)",                             {},                       bool,         R_ENDINGS),
    row("A15", "num(1.0) < 1j",                                    {},                       TypeError,    R_ENDINGS),
    row("A16", "math.comb(num(4.0), 2)",                           {},                       TypeError,    R_SCOPE),
    row("A16", "math.factorial(num(4.0))",                         {},                       TypeError,    R_SCOPE),
    row("A16", "math.gcd(num(4.0), 2)",                            {},                       TypeError,    R_SCOPE),
    row("A16", "math.isqrt(num(4.0))",                             {},                       TypeError,    R_SCOPE),
    row("A16", "math.lcm(num(4.0), 2)",                            {},                       TypeError,    R_SCOPE),
    row("A12", "num(2.0) * np.array([1.0])",                       {},                       TypeError,    R_SCOPE, requires="numpy", plain_parity=False, probe=_NUMPY_MUL_ARRAY),
    row("A12", "num(2.0) * np.float32(1.0)",                       {},                       TypeError,    R_SCOPE, requires="numpy", plain_parity=False, probe=_NUMPY_MUL_FLOAT32),
    row("A12", "num(1.0) + np.float64(2.0)",                       {"ADD": 1},               CF,           R_SCOPE, requires="numpy", plain_parity=False, probe=_NUMPY_FLOAT64_LEFT),
    row("A12", "np.float64(2.0) + num(1.0)",                       {"ADD": 1},               CF,           R_SCOPE, requires="numpy", plain_parity=False, probe=_NUMPY_FLOAT64_RIGHT),
    row("A16", "math.perm(num(4.0), 2)",                           {},                       TypeError,    R_SCOPE),
    row("A17", "(num(3.0) * 2.0) * 4.0",                           {"MUL": 2},               CF,           R_RULES),
    row("A17", "-(-num(3.0))",                                     {"MINUS": 2},             CF,           R_RULES),
]
# fmt: on
