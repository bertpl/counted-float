from enum import StrEnum


class FlopType(StrEnum):
    """
    Enum describing the different types of floating-point operations,
    each of which are counted separately and can potentially have different weights.
    --> See: /docs/analysis_methodology.md
    """

    ABS = "abs(x)"
    MINUS = "-x"
    COMP = "x<=y"  # includes x>=y, x==y, x<y, x>y, as well as comparison to 0
    RND = "round"  # round float -> float
    F2I = "float->int"  # float -> int, also includes round(x), math.floor(x), math.ceil(x)
    I2F = "int->float"  # int -> float
    ADD = "x+y"
    SUB = "x-y"
    MUL = "x*y"
    DIV = "x/y"
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

    def long_name(self) -> str:
        return f"FlopType.{self.name:<9}  [{self.value}]"
