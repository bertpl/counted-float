"""Section A holds the cross-cutting regime decisions.

Rows A5 (outside any context) and A6 (paused) need a context arrangement the shared runner
deliberately does not model; they are pinned by dedicated tests in `test_golden_counting`.
"""

import math
from decimal import Decimal
from fractions import Fraction

from counted_float import CountedFloat

from ._row import (
    I_CLASSIFIERS,
    R_CONTRACT,
    R_ENDINGS,
    R_PORT,
    R_RECORDS,
    R_SCOPE,
    GoldenRow,
)


def _numpy_probe(expression):
    """Wrap a numpy-dependent probe so the module imports without numpy installed."""

    def probe(number_type: type) -> object:
        import numpy as np

        return expression(number_type, np)

    return probe


ROWS: list[GoldenRow] = [
    GoldenRow("A1", "plain-only sqrt(2.0)", lambda num: math.sqrt(2.0), {}, float, cites=(R_CONTRACT,)),
    GoldenRow("A1", "plain-only sqrt(3) int", lambda num: math.sqrt(3), {}, float, cites=(R_CONTRACT,)),
    GoldenRow("A2", "contagion sqrt(cf)", lambda num: math.sqrt(num(2.0)), {"SQRT": 1}, CountedFloat, cites=(R_PORT,)),
    GoldenRow(
        "A2",
        "plain wins, wrapped: fmax(cf nan, 1.0)",
        lambda num: math.fmax(num(math.nan), 1.0),
        {"COMP": 1},
        CountedFloat,
        requires="fmax",
        cites=(R_PORT,),
    ),
    GoldenRow(
        "A3",
        "non-float exits round(cf) / cf < 2.0",
        lambda num: (round(num(2.7)), num(1.0) < 2.0),
        {"COMP": 1, "F2I": 1},
        (int, bool),
        cites=(R_ENDINGS,),
    ),
    GoldenRow(
        "A4", "raising sqrt(cf(-1))", lambda num: math.sqrt(num(-1.0)), {}, raises=ValueError, cites=(R_RECORDS,)
    ),
    GoldenRow("A4", "raising log(cf(-1))", lambda num: math.log(num(-1.0)), {}, raises=ValueError, cites=(R_RECORDS,)),
    GoldenRow(
        "A4", "raising fmod(cf, 0.0)", lambda num: math.fmod(num(1.0), 0.0), {}, raises=ValueError, cites=(R_RECORDS,)
    ),
    GoldenRow("A4", "raising cf / 0.0", lambda num: num(1.0) / 0.0, {}, raises=ZeroDivisionError, cites=(R_RECORDS,)),
    GoldenRow("A4", "raising cf % 0.0", lambda num: num(1.0) % 0.0, {}, raises=ZeroDivisionError, cites=(R_RECORDS,)),
    GoldenRow("A4", "raising CF(10**400)", lambda num: num(10**400), {}, raises=OverflowError, cites=(R_RECORDS,)),
    GoldenRow(
        "A4",
        "raising element prod([cf, cf, None])",
        lambda num: math.prod([num(2.0), num(3.0), None]),
        {},
        raises=TypeError,
        cites=(R_RECORDS,),
    ),
    GoldenRow(
        "A4",
        "raising first prod([cf, None])",
        lambda num: math.prod([num(2.0), None]),
        {},
        raises=TypeError,
        cites=(R_RECORDS,),
    ),
    GoldenRow("A7", "int constant cf + 2", lambda num: num(1.0) + 2, {"ADD": 1}, CountedFloat, cites=(R_CONTRACT,)),
    GoldenRow(
        "A7", "bool constant cf + True", lambda num: num(1.0) + True, {"ADD": 1}, CountedFloat, cites=(R_CONTRACT,)
    ),
    GoldenRow("A8", "CF(5) int source", lambda num: num(5), {"I2F": 1}, CountedFloat, cites=(R_SCOPE,)),
    GoldenRow("A8", "CF(True) bool source", lambda num: num(True), {"I2F": 1}, CountedFloat, cites=(R_SCOPE,)),
    GoldenRow(
        "A8",
        "CF.from_number(5)",
        lambda num: num.from_number(5),
        {"I2F": 1},
        CountedFloat,
        requires="from_number",
        cites=(R_SCOPE,),
    ),
    GoldenRow("A9", "cf + Decimal", lambda num: num(1.0) + Decimal("1.5"), {}, raises=TypeError, cites=(R_SCOPE,)),
    GoldenRow(
        "A10",
        "cf == Decimal / cf < Decimal",
        lambda num: (num(1.5) == Decimal("1.5"), num(1.5) < Decimal("2.5")),
        {},
        (bool, bool),
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "A11", "cf + Fraction ends countedness", lambda num: num(1.0) + Fraction(1, 2), {}, float, cites=(R_ENDINGS,)
    ),
    GoldenRow(
        "A12",
        "Fraction + cf counts",
        lambda num: Fraction(1, 2) + num(1.0),
        {"ADD": 1},
        CountedFloat,
        cites=(R_RECORDS,),
    ),
    GoldenRow(
        "A13",
        "cf < Fraction guard costs",
        lambda num: num(0.3) < Fraction(1, 2),
        {"ABS": 1, "COMP": 2},
        bool,
        cites=(R_RECORDS, I_CLASSIFIERS),
    ),
    GoldenRow(
        "A14",
        "cf * np.array raises",
        _numpy_probe(lambda num, np: num(2.0) * np.array([1.0])),
        {},
        raises=TypeError,
        requires="numpy",
        cites=(R_SCOPE,),
        twin=False,
    ),
    GoldenRow(
        "A14",
        "cf * np.float32 raises",
        _numpy_probe(lambda num, np: num(2.0) * np.float32(1.0)),
        {},
        raises=TypeError,
        requires="numpy",
        cites=(R_SCOPE,),
        twin=False,
    ),
    GoldenRow(
        "A14",
        "np.float64 flows as plain constant",
        _numpy_probe(lambda num, np: (num(1.0) + np.float64(2.0), np.float64(2.0) + num(1.0))),
        {"ADD": 2},
        (CountedFloat, CountedFloat),
        requires="numpy",
        cites=(R_SCOPE,),
        twin=False,
    ),
    GoldenRow(
        "A15",
        "divmod carries countedness per element",
        lambda num: divmod(num(7.0), 3.0),
        {"DIV": 1, "MUL": 1, "RND": 1, "SUB": 1},
        (CountedFloat, CountedFloat),
        cites=(R_PORT,),
    ),
    GoldenRow(
        "A16",
        "complex arithmetic exits at zero",
        lambda num: (num(1.0) + 1j, num(1.0) * (2 + 3j)),
        {},
        (complex, complex),
        cites=(R_ENDINGS,),
    ),
    GoldenRow(
        "A17",
        "complex equality delegates at zero",
        lambda num: (num(1.0) == 1j, num(1.0) == (1 + 0j)),
        {},
        (bool, bool),
        cites=(R_ENDINGS,),
    ),
    GoldenRow("A17", "complex ordering raises", lambda num: num(1.0) < 1j, {}, raises=TypeError, cites=(R_ENDINGS,)),
    GoldenRow(
        "A18",
        "integer-domain comb rejects cf",
        lambda num: math.comb(num(4.0), 2),
        {},
        raises=TypeError,
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "A18",
        "integer-domain factorial rejects cf",
        lambda num: math.factorial(num(4.0)),
        {},
        raises=TypeError,
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "A18",
        "integer-domain gcd rejects cf",
        lambda num: math.gcd(num(4.0), 2),
        {},
        raises=TypeError,
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "A18",
        "integer-domain isqrt rejects cf",
        lambda num: math.isqrt(num(4.0)),
        {},
        raises=TypeError,
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "A18",
        "integer-domain lcm rejects cf",
        lambda num: math.lcm(num(4.0), 2),
        {},
        raises=TypeError,
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "A18",
        "integer-domain perm rejects cf",
        lambda num: math.perm(num(4.0), 2),
        {},
        raises=TypeError,
        cites=(R_SCOPE,),
    ),
]
