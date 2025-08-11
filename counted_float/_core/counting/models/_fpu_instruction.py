from counted_float._core._backwards_compat import StrEnum


class FPUInstruction(StrEnum):
    """
    Enum of relevant x87 FPU instructions.
    Background:
      - [FIL] "Simply FPU", by Raymond Filiatreault, available at: https://masm32.com/masmcode/rayfil/tutorial/index.html
    """

    FABS = "FABS"  # absolute value of float
    FCHS = "FCHS"  # change sign of float
    FCOM = "FCOM"  # compare two floats (a == b, a > b, a < b)
    FTST = "FTST"  # test if float is zero (a >= 0)
    FRNDINT = "FRNDINT"  # round float to integer (ceil or floor)
    FADD = "FADD"  # addition of two floats (a + b)
    FSUB = "FSUB"  # subtraction of two floats (a - b)
    FMUL = "FMUL"  # multiplication of two floats (a * b)
    FDIV = "FDIV"  # division of two floats (a / b)
    FSQRT = "FSQRT"  # square root of float (sqrt(a))
    F2XM1 = "F2XM1"  # 2 raised to the power of float minus 1 (2**a - 1)
    FYL2X = "FYL2X"  # logarithm base 2 of float (log2(a))
