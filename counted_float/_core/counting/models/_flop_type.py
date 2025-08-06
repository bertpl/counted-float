from counted_float._core._backwards_compat import StrEnum


class FlopType(StrEnum):
    """
    Enum describing the different types of floating-point operations,
    each of which are counted separately and can potentially have different weights.

    Enum                Math                                    ~corresponding
    Member              Operation                               x87 instruction(s)
    -------             ----------                              -------------------

    ABS                 abs(x)                                  FABS
    MINUS               -x                                      FCHS
    EQUALS              x == y                                  FCOM
    GTE                 x >= y                                  FCOM
    LTE                 x <= y                                  FCOM
    CMP_ZERO            x >= 0                                  FTST
    RND                 ceil(x) or floor(x)                     FRNDINT
    ADD                 x + y                                   FADD
    SUB                 x - y                                   FSUB
    MUL                 x * y                                   FMUL
    DIV                 x / y                                   FDIV
    SQRT                sqrt(x)                                 FSQRT
    POW2                2**x                                    > F2XM1
    LOG2                log2(x)                                 FYLX2
    POW                 x**y                                    > F2XM1 + FYLX2 + FMUL
    """

    ABS = "abs(x)"
    MINUS = "-x"
    EQUALS = "x==y"
    GTE = "x>=y"
    LTE = "x<=y"
    CMP_ZERO = "x>=0"
    RND = "round(x)"
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
