"""Corpus section D — the float surface and the countedness exits (rows D1–D15)."""

import copy
import math
import pickle
from decimal import Decimal
from fractions import Fraction

from counted_float import CountedFloat

from ._row import R_CONTRACT, R_ENDINGS, R_RECORDS, R_SCOPE, GoldenRow

CF = CountedFloat

ROWS: list[GoldenRow] = [
    GoldenRow("D1", "int(cf)", lambda num: int(num(2.7)), {"F2I": 1}, int, cites=(R_ENDINGS,)),
    GoldenRow(
        "D1",
        "floor/ceil/trunc(cf)",
        lambda num: (math.floor(num(2.7)), math.ceil(num(2.2)), math.trunc(num(2.7))),
        {"F2I": 3},
        (int, int, int),
        cites=(R_ENDINGS,),
    ),
    GoldenRow("D2", "float(cf) opt-out", lambda num: float(num(2.7)), {}, float, cites=(R_CONTRACT,)),
    GoldenRow("D3", "bool(cf) truthiness free", lambda num: bool(num(2.7)), {}, bool, cites=(R_ENDINGS,)),
    GoldenRow("D4", "repr(cf) shows the type", lambda num: repr(num(1.5)), {}, str, cites=(R_ENDINGS,), twin=False),
    GoldenRow("D4", "f-string format", lambda num: f"{num(1.5):.2f}", {}, str, cites=(R_ENDINGS,)),
    GoldenRow("D5", "percent format free", lambda num: f"{num(0.5):.1%}", {}, str, cites=(R_ENDINGS,)),
    GoldenRow("D6", "as_integer_ratio()", lambda num: num(2.5).as_integer_ratio(), {}, (int, int), cites=(R_ENDINGS,)),
    GoldenRow("D7", "frexp(cf)", lambda num: math.frexp(num(8.0)), {}, (float, int), cites=(R_ENDINGS,)),
    GoldenRow(
        "D7",
        "ldexp/modf/nextafter/ulp uncounted",
        lambda num: (
            math.ldexp(num(2.0), 2),
            math.modf(num(2.5))[0],
            math.nextafter(num(1.0), 2.0),
            math.ulp(num(1.0)),
        ),
        {},
        (float, float, float, float),
        cites=(R_ENDINGS,),
    ),
    GoldenRow(
        "D8",
        "hex() out / fromhex() in",
        lambda num: (num(2.5).hex(), num.fromhex("0x1.8p+1")),
        {},
        (str, CF),
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "D9",
        "real / conjugate() stay counted",
        lambda num: (num(2.5).real, num(2.5).conjugate()),
        {},
        (CF, CF),
        cites=(R_ENDINGS,),
    ),
    GoldenRow("D10", "imag is a port constant", lambda num: num(2.5).imag, {}, float, cites=(R_ENDINGS,)),
    GoldenRow("D11", "CF(5) construction I2F", lambda num: num(5), {"I2F": 1}, CF, cites=(R_SCOPE,)),
    GoldenRow(
        "D12",
        "CF(2.5) / CF(Decimal) free",
        lambda num: (num(2.5), num(Decimal("1.5"))),
        {},
        (CF, CF),
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "D12",
        "CF.from_number(2.5) free",
        lambda num: num.from_number(2.5),
        {},
        CF,
        requires="from_number",
        cites=(R_SCOPE,),
    ),
    GoldenRow(
        "D13",
        "pickle round-trip keeps type",
        lambda num: pickle.loads(pickle.dumps(num(2.5))),  # noqa: S301 -- round-trips a literal
        {},
        CF,
        cites=(R_CONTRACT,),
    ),
    GoldenRow("D13", "deepcopy keeps type", lambda num: copy.deepcopy(num(2.5)), {}, CF, cites=(R_CONTRACT,)),
    GoldenRow(
        "D14",
        "set membership costs the probe",
        lambda num: num(2.0) in {num(2.0)},
        {"COMP": 1},
        bool,
        cites=(R_RECORDS,),
    ),
    GoldenRow(
        "D14",
        "identity hit skips the compare",
        lambda num: (lambda x: x in {x})(num(2.0)),
        {},
        bool,
        cites=(R_RECORDS,),
    ),
    GoldenRow("D14", "hash(cf) alone free", lambda num: hash(num(2.5)), {}, int, cites=(R_RECORDS,)),
    GoldenRow(
        "D15",
        "conversions out of the domain",
        lambda num: (complex(num(2.5)), Decimal(num(2.5)), Fraction(num(2.5))),
        {},
        (complex, Decimal, Fraction),
        cites=(R_ENDINGS,),
    ),
]
