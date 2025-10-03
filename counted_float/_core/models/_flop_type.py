from counted_float._core.compatibility import StrEnum


class FlopType(StrEnum):
    """
    Enum describing the different types of floating-point operations,
    each of which are counted separately and can potentially have different weights.
    --> See: /docs/analysis_methodology.md
    """

    ABS = "abs(x)"
    MINUS = "-x"
    EQUALS = "x==y"
    GTE = "x>=y"
    LTE = "x<=y"
    CMP_ZERO = "x>=0"
    RND = "round(x)"  # float -> float
    F2I = "int(x)"  # float -> int, also includes math.floor(x), math.ceil(x)
    I2F = "float(x)"  # int -> float
    ADD = "x+y"
    SUB = "x-y"
    MUL = "x*y"
    DIV = "x/y"
    SQRT = "sqrt(x)"
    POW2 = "2^x"
    LOG2 = "log2(x)"
    POW = "x^y"

    def long_name(self) -> str:
        return f"FlopType.{self.name:<9}  [{self.value}]"
