"""Section B holds the uniform operations, each with one fixed tally per call.

Snippets run over the injected `num` — `CountedFloat` counted, plain `float` for the twin run.
"""

from counted_float import CountedFloat
from tests.counting.golden.schema import (
    I_CLASSIFIERS,
    I_FMAX_COMP,
    I_FORMULA_FIXED,
    R_RULES,
    CorpusRow,
    flat,
    row,
)

CF = CountedFloat

# fmt: off
ROWS: list[CorpusRow] = flat([
    row("B1",  "math.sqrt(num(2.0))",                    {"SQRT": 1},     CF,    R_RULES),
    row("B2",  "math.cbrt(num(2.0))",                    {"CBRT": 1},     CF,    R_RULES),
    row("B3",  "math.exp(num(0.5))",                     {"EXP": 1},      CF,    R_RULES),
    row("B4",  "math.exp2(num(0.5))",                    {"EXP2": 1},     CF,    R_RULES),
    row("B5",  "math.expm1(num(0.5))",                   {"EXPM1": 1},    CF,    R_RULES),
    row("B6",  "math.log1p(num(0.5))",                   {"LOG1P": 1},    CF,    R_RULES),
    row("B7",  "math.log2(num(8.0))",                    {"LOG2": 1},     CF,    R_RULES),
    row("B8",  "math.log10(num(100.0))",                 {"LOG10": 1},    CF,    R_RULES),
    row("B9",  "math.sin(num(0.5))",                     {"SIN": 1},      CF,    R_RULES),
    row("B10", "math.cos(num(0.5))",                     {"COS": 1},      CF,    R_RULES),
    row("B11", "math.tan(num(0.5))",                     {"TAN": 1},      CF,    R_RULES),
    row("B12", "math.asin(num(0.5))",                    {"ASIN": 1},     CF,    R_RULES),
    row("B13", "math.acos(num(0.5))",                    {"ACOS": 1},     CF,    R_RULES),
    row("B14", "math.atan(num(0.5))",                    {"ATAN": 1},     CF,    R_RULES),
    row("B15", "math.sinh(num(0.5))",                    {"SINH": 1},     CF,    R_RULES),
    row("B16", "math.cosh(num(0.5))",                    {"COSH": 1},     CF,    R_RULES),
    row("B17", "math.tanh(num(0.5))",                    {"TANH": 1},     CF,    R_RULES),
    row("B18", "math.asinh(num(0.5))",                   {"ASINH": 1},    CF,    R_RULES),
    row("B19", "math.acosh(num(2.0))",                   {"ACOSH": 1},    CF,    R_RULES),
    row("B20", "math.atanh(num(0.5))",                   {"ATANH": 1},    CF,    R_RULES),
    row("B21", "math.gamma(num(2.5))",                   {"GAMMA": 1},    CF,    R_RULES),
    row("B22", "math.lgamma(num(2.5))",                  {"LGAMMA": 1},   CF,    R_RULES),
    row("B23", "math.erf(num(0.5))",                     {"ERF": 1},      CF,    R_RULES),
    row("B24", "math.erfc(num(0.5))",                    {"ERFC": 1},     CF,    R_RULES),
    row("B25", "math.fabs(num(-2.0))",                   {"ABS": 1},      CF,    R_RULES),
    row("B26", "math.degrees(num(1.0))",                 {"MUL": 1},      CF,    R_RULES),
    row("B27", "math.radians(num(90.0))",                {"MUL": 1},      CF,    R_RULES),
    row("B28", "math.atan2(num(1.0), num(2.0))",         {"ATAN2": 1},    CF,    R_RULES),
    row("B29", "math.fmod(num(5.0), num(3.0))",          {"FMOD": 1},     CF,    R_RULES),
    row("B30", "math.remainder(num(5.0), num(3.0))",     {"REMAINDER": 1}, CF,   R_RULES),
    row("B31", "math.copysign(num(3.0), num(-2.0))",     {"COPYSIGN": 1}, CF,    R_RULES),
    row("B32", "math.fmax(num(2.0), num(3.0))",          {"COMP": 1},     CF,    I_FMAX_COMP, requires="fmax"),
    row("B33", "math.fmin(num(2.0), num(3.0))",          {"COMP": 1},     CF,    I_FMAX_COMP, requires="fmin"),
    row("B34", "math.isnan(num(2.0))",                   {"COMP": 1},           bool, I_CLASSIFIERS),
    row("B35", "math.isinf(num(2.0))",                   {"ABS": 1, "COMP": 1}, bool, I_CLASSIFIERS),
    row("B36", "math.isfinite(num(2.0))",                {"ABS": 1, "COMP": 1}, bool, I_CLASSIFIERS),
    row("B37", "math.isnormal(num(2.0))",                {"ABS": 1, "COMP": 2}, bool, I_CLASSIFIERS, requires="isnormal"),
    row("B38", "math.issubnormal(num(5e-324))",          {"ABS": 1, "COMP": 2}, bool, I_CLASSIFIERS, requires="issubnormal"),
    row("B39", "math.signbit(num(-2.0))",                {"COMP": 1},           bool, I_CLASSIFIERS, requires="signbit"),
    row("B40", "math.isclose(num(2.0), 2.5)",            {"ABS": 3, "COMP": 3, "MUL": 1, "SUB": 1}, bool, I_FORMULA_FIXED),
    row("B40", "math.isclose(num(math.inf), 1.0)",       {"ABS": 3, "COMP": 3, "MUL": 1, "SUB": 1}, bool, I_FORMULA_FIXED),
    row("B41", "math.fsum([num(0.1)] * 4)",              {"ADD": 3},      CF,    I_FORMULA_FIXED),
    row("B41", "math.fsum([num(0.1)])",                  {},              CF,    I_FORMULA_FIXED, reinforces=True),
])
# fmt: on
