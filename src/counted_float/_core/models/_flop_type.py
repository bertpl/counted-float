from enum import StrEnum


class FlopType(StrEnum):
    """Enum describing the different types of floating-point operations.

    Each of these are counted separately and can potentially have different weights.
    --> See: /docs/analysis_methodology.md.
    """

    ABS = "abs(x)"
    MINUS = "-x"
    COPYSIGN = "copysign(x,y)"  # sign-bit transfer; same instruction class as ABS/MINUS, but 1-3 ops depending on arch
    COMP = "x<=y"  # includes x>=y, x==y, x<y, x>y, as well as comparison to 0
    RND = "round"  # round float -> float
    F2I = "float->int"  # float -> int, also includes round(x), math.floor(x), math.ceil(x)
    I2F = "int->float"  # int -> float
    ADD = "x+y"
    SUB = "x-y"
    MUL = "x*y"
    DIV = "x/y"
    FMA = "x*y+z"  # fused multiply-add: one instruction, one rounding
    SQRT = "sqrt(x)"
    CBRT = "cbrt(x)"
    EXP = "e^x"
    EXP2 = "2^x"
    EXP10 = "10^x"
    LOG = "log(x)"
    LOG2 = "log2(x)"
    LOG10 = "log10(x)"
    POW = "x^y"
    SIN = "sin(x)"
    COS = "cos(x)"
    TAN = "tan(x)"
    ASIN = "asin(x)"
    ACOS = "acos(x)"
    ATAN = "atan(x)"
    ATAN2 = "atan2(y,x)"
    HYPOT = "hypot(x,y)"
    EXPM1 = "expm1(x)"
    LOG1P = "log1p(x)"
    FMOD = "fmod(x,y)"
    SINH = "sinh(x)"
    COSH = "cosh(x)"
    TANH = "tanh(x)"
    ASINH = "asinh(x)"
    ACOSH = "acosh(x)"
    ATANH = "atanh(x)"

    def long_name(self) -> str:
        return f"FlopType.{self.name:<9}  [{self.value}]"
