"""Section D holds the float surface and the countedness exits.

Snippets run over the injected `num` — `CountedFloat` counted, plain `float` for the twin run.
"""

from decimal import Decimal
from fractions import Fraction

from counted_float import CountedFloat
from tests.counting.golden.schema import R_CONTRACT, R_ENDINGS, R_RECORDS, R_SCOPE, CorpusRow, flat, row

CF = CountedFloat

# fmt: off
ROWS: list[CorpusRow] = flat([
    row("D1",  "int(num(2.7))",                                              {"F2I": 1},  int,                R_ENDINGS),
    row("D1",  "math.floor(num(2.7))",                                       {"F2I": 1},  int,                R_ENDINGS),
    row("D1",  "math.ceil(num(2.2))",                                        {"F2I": 1},  int,                R_ENDINGS),
    row("D1",  "math.trunc(num(2.7))",                                       {"F2I": 1},  int,                R_ENDINGS),
    row("D2",  "float(num(2.7))",                                            {},          float,              R_CONTRACT),
    row("D3",  "bool(num(2.7))",                                             {},          bool,               R_ENDINGS),
    row("D4",  "repr(num(1.5))",                                             {},          str,                R_ENDINGS, plain_parity=False),
    row("D4",  "f'{num(1.5):.2f}'",                                          {},          str,                R_ENDINGS),
    row("D5",  "f'{num(0.5):.1%}'",                                          {},          str,                R_ENDINGS),
    row("D6",  "num(2.5).as_integer_ratio()",                                {},          (int, int),         R_ENDINGS),
    row("D7",  "math.frexp(num(8.0))",                                       {},          (float, int),       R_ENDINGS),
    row("D7",  "math.ldexp(num(2.0), 2)",                                    {},          float,              R_ENDINGS),
    row("D7",  "math.modf(num(2.5))",                                        {},          (float, float),     R_ENDINGS),
    row("D7",  "math.nextafter(num(1.0), 2.0)",                              {},          float,              R_ENDINGS),
    row("D7",  "math.ulp(num(1.0))",                                         {},          float,              R_ENDINGS),
    row("D8",  "num(2.5).hex()",                                             {},          str,                R_SCOPE),
    row("D8",  "num.fromhex('0x1.8p+1')",                                    {},          CF,                 R_SCOPE),
    row("D9",  "num(2.5).real",                                              {},          CF,                 R_ENDINGS),
    row("D9",  "num(2.5).conjugate()",                                       {},          CF,                 R_ENDINGS),
    row("D10", "num(2.5).imag",                                              {},          float,              R_ENDINGS),
    row("D11", "num(5)",                                                     {"I2F": 1},  CF,                 R_SCOPE),
    row("D12", "num(2.5)",                                                   {},          CF,                 R_SCOPE),
    row("D12", "num(Decimal('1.5'))",                                        {},          CF,                 R_SCOPE),
    row("D12", "num.from_number(2.5)",                                       {},          CF,                 R_SCOPE, requires="from_number"),
    row("D13", "pickle.loads(pickle.dumps(num(2.5)))",                       {},          CF,                 R_CONTRACT),
    row("D13", "copy.deepcopy(num(2.5))",                                    {},          CF,                 R_CONTRACT),
    row("D14", "num(2.0) in {num(2.0)}",                                     {"COMP": 1}, bool,               R_RECORDS),
    row("D14", "(lambda x: x in {x})(num(2.0))",                             {},          bool,               R_RECORDS),
    row("D14", "hash(num(2.5))",                                             {},          int,                R_RECORDS),
    row("D15", "complex(num(2.5))",                                          {},          complex,            R_ENDINGS),
    row("D15", "Decimal(num(2.5))",                                          {},          Decimal,            R_ENDINGS),
    row("D15", "Fraction(num(2.5))",                                         {},          Fraction,           R_ENDINGS),
])
# fmt: on
