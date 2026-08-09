"""Section B holds the uniform operations, each with one fixed tally per call."""

import math

from counted_float import CountedFloat

from ._row import (
    I_CLASSIFIERS,
    I_FMAX_COMP,
    I_FORMULA_FIXED,
    R_RULES,
    GoldenRow,
)

# Each entry is (row_id, math name, flop type, probe argument); one benchmarked weight per call.
_UNARY_OWN_TYPE = [
    ("B1", "sqrt", "SQRT", 2.0),
    ("B2", "cbrt", "CBRT", 2.0),
    ("B3", "exp", "EXP", 0.5),
    ("B4", "exp2", "EXP2", 0.5),
    ("B5", "expm1", "EXPM1", 0.5),
    ("B6", "log1p", "LOG1P", 0.5),
    ("B7", "log2", "LOG2", 8.0),
    ("B8", "log10", "LOG10", 100.0),
    ("B9", "sin", "SIN", 0.5),
    ("B10", "cos", "COS", 0.5),
    ("B11", "tan", "TAN", 0.5),
    ("B12", "asin", "ASIN", 0.5),
    ("B13", "acos", "ACOS", 0.5),
    ("B14", "atan", "ATAN", 0.5),
    ("B15", "sinh", "SINH", 0.5),
    ("B16", "cosh", "COSH", 0.5),
    ("B17", "tanh", "TANH", 0.5),
    ("B18", "asinh", "ASINH", 0.5),
    ("B19", "acosh", "ACOSH", 2.0),
    ("B20", "atanh", "ATANH", 0.5),
    ("B21", "gamma", "GAMMA", 2.5),
    ("B22", "lgamma", "LGAMMA", 2.5),
    ("B23", "erf", "ERF", 0.5),
    ("B24", "erfc", "ERFC", 0.5),
    ("B25", "fabs", "ABS", -2.0),
]

# Each entry is (row_id, math name, flop type, probe arguments); binary calls with a weight of their own.
_BINARY_OWN_TYPE = [
    ("B28", "atan2", "ATAN2", (1.0, 2.0)),
    ("B29", "fmod", "FMOD", (5.0, 3.0)),
    ("B30", "remainder", "REMAINDER", (5.0, 3.0)),
    ("B31", "copysign", "COPYSIGN", (3.0, -2.0)),
]

# Each entry is (row_id, math name, counts, probe argument); the bool-returning classifiers.
_CLASSIFIERS = [
    ("B34", "isnan", {"COMP": 1}, 2.0),
    ("B35", "isinf", {"ABS": 1, "COMP": 1}, 2.0),
    ("B36", "isfinite", {"ABS": 1, "COMP": 1}, 2.0),
]
_CLASSIFIERS_GATED = [
    ("B37", "isnormal", {"ABS": 1, "COMP": 2}, 2.0),
    ("B38", "issubnormal", {"ABS": 1, "COMP": 2}, 5e-324),
    ("B39", "signbit", {"COMP": 1}, -2.0),
]


def _unary(name: str, arg: float):
    """Build a one-argument `math` probe over the injected number type."""
    return lambda num: getattr(math, name)(num(arg))


def _binary(name: str, args: tuple[float, float]):
    """Build a two-argument `math` probe with both operands counted."""
    return lambda num: getattr(math, name)(num(args[0]), num(args[1]))


ROWS: list[GoldenRow] = [
    *(
        GoldenRow(row_id, f"{name}(cf)", _unary(name, arg), {flop_type: 1}, CountedFloat, cites=(R_RULES,))
        for row_id, name, flop_type, arg in _UNARY_OWN_TYPE
    ),
    GoldenRow("B26", "degrees(cf)", _unary("degrees", 1.0), {"MUL": 1}, CountedFloat, cites=(R_RULES,)),
    GoldenRow("B27", "radians(cf)", _unary("radians", 90.0), {"MUL": 1}, CountedFloat, cites=(R_RULES,)),
    *(
        GoldenRow(row_id, f"{name}(cf, cf)", _binary(name, args), {flop_type: 1}, CountedFloat, cites=(R_RULES,))
        for row_id, name, flop_type, args in _BINARY_OWN_TYPE
    ),
    GoldenRow(
        "B32",
        "fmax(cf, cf)",
        _binary("fmax", (2.0, 3.0)),
        {"COMP": 1},
        CountedFloat,
        requires="fmax",
        cites=(I_FMAX_COMP,),
    ),
    GoldenRow(
        "B33",
        "fmin(cf, cf)",
        _binary("fmin", (2.0, 3.0)),
        {"COMP": 1},
        CountedFloat,
        requires="fmin",
        cites=(I_FMAX_COMP,),
    ),
    *(
        GoldenRow(row_id, f"{name}(cf)", _unary(name, arg), counts, bool, cites=(I_CLASSIFIERS,))
        for row_id, name, counts, arg in _CLASSIFIERS
    ),
    *(
        GoldenRow(row_id, f"{name}(cf)", _unary(name, arg), counts, bool, requires=name, cites=(I_CLASSIFIERS,))
        for row_id, name, counts, arg in _CLASSIFIERS_GATED
    ),
    GoldenRow(
        "B40",
        "isclose(cf, 2.5)",
        lambda num: math.isclose(num(2.0), 2.5),
        {"ABS": 3, "COMP": 3, "MUL": 1, "SUB": 1},
        bool,
        cites=(I_FORMULA_FIXED,),
    ),
    GoldenRow(
        "B40",
        "isclose(cf, inf regime) same fixed price",
        lambda num: math.isclose(num(math.inf), 1.0),
        {"ABS": 3, "COMP": 3, "MUL": 1, "SUB": 1},
        bool,
        cites=(I_FORMULA_FIXED,),
    ),
    GoldenRow(
        "B41",
        "fsum(4 x cf)",
        lambda num: math.fsum([num(0.1)] * 4),
        {"ADD": 3},
        CountedFloat,
        cites=(I_FORMULA_FIXED,),
    ),
    GoldenRow(
        "B41",
        "fsum([cf]) single element",
        lambda num: math.fsum([num(0.1)]),
        {},
        CountedFloat,
        cites=(I_FORMULA_FIXED,),
        reinforces=True,
    ),
]
