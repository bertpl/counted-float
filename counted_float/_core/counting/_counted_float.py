from __future__ import annotations

import math

from counted_float._core.models import FlopCounts

from ._global_counter import GLOBAL_COUNTER


class CountedFloat(float):
    # -------------------------------------------------------------------------
    #  FLOP COUNTING
    # -------------------------------------------------------------------------
    @classmethod
    def get_global_flop_counts(cls) -> FlopCounts:
        """
        Returns the global FLOP counts for all CountedFloat instances.
        """
        return GLOBAL_COUNTER.flop_counts()

    # -------------------------------------------------------------------------
    #  CONSTRUCTOR
    # -------------------------------------------------------------------------
    def __new__(cls, value: float | int):
        if isinstance(value, int):
            GLOBAL_COUNTER.incr_i2f()
        self = super().__new__(cls, float(value))
        return self

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"CountedFloat({super().__repr__()})"

    def __hash__(self):
        return super().__hash__()

    # -------------------------------------------------------------------------
    #  OVERLOADED MATH OPERATIONS
    # -------------------------------------------------------------------------
    def __abs__(self) -> CountedFloat:
        """abs(x)"""
        GLOBAL_COUNTER.incr_abs()
        return CountedFloat(super().__abs__())

    def __neg__(self) -> CountedFloat:
        """-x"""
        GLOBAL_COUNTER.incr_minus()
        return CountedFloat(super().__neg__())

    def __eq__(self, other) -> bool:
        """x==other or other==x"""
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return super().__eq__(other)

    def __ne__(self, other) -> bool:
        """x!=other or other!=x"""
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return super().__ne__(other)

    def __lt__(self, other):
        """x<other"""
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return super().__lt__(other)

    def __le__(self, other):
        """x<=other"""
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return super().__le__(other)

    def __gt__(self, other):
        """x>other"""
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return super().__gt__(other)

    def __ge__(self, other):
        """x>=other"""
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return super().__ge__(other)

    def __round__(self, n=None) -> int:
        """
        round(x, n)
          n = None -> round to nearest integer and return int
          n = 0    -> round to nearest integer and return float
          n > 0    -> round to n decimal places and return float
        """
        if n is None:
            GLOBAL_COUNTER.incr_f2i()  # will round and return int
        else:
            GLOBAL_COUNTER.incr_rnd()  # will round and return float

        return super().__round__(n)

    def __floor__(self) -> int:
        """math.floor(x)"""
        GLOBAL_COUNTER.incr_f2i()
        return super().__floor__()

    def __ceil__(self) -> int:
        """math.ceil(x)"""
        GLOBAL_COUNTER.incr_f2i()
        return super().__ceil__()

    def __int__(self) -> int:
        """int(x)"""
        GLOBAL_COUNTER.incr_f2i()
        return super().__int__()

    def __trunc__(self) -> int:
        """int(x)"""
        GLOBAL_COUNTER.incr_f2i()
        return super().__trunc__()

    def __add__(self, other) -> CountedFloat:
        """x+other"""
        GLOBAL_COUNTER.incr_add()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__add__(other))

    def __radd__(self, other) -> CountedFloat:
        """other+x"""
        GLOBAL_COUNTER.incr_add()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__radd__(other))

    def __sub__(self, other) -> CountedFloat:
        """x-other"""
        GLOBAL_COUNTER.incr_sub()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__sub__(other))

    def __rsub__(self, other) -> CountedFloat:
        """other-x"""
        GLOBAL_COUNTER.incr_sub()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__rsub__(other))

    def __mul__(self, other) -> CountedFloat:
        """x*other or other*x"""
        GLOBAL_COUNTER.incr_mul()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__mul__(other))

    def __rmul__(self, other) -> CountedFloat:
        """other*x"""
        GLOBAL_COUNTER.incr_mul()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__rmul__(other))

    def __truediv__(self, other) -> CountedFloat:
        """x/other"""
        GLOBAL_COUNTER.incr_div()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__truediv__(other))

    def __rtruediv__(self, other) -> CountedFloat:
        """other/x"""
        GLOBAL_COUNTER.incr_div()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(super().__rtruediv__(other))

    def __pow__(self, other) -> CountedFloat:
        """x**other"""
        if isinstance(other, int) and other == 2:
            GLOBAL_COUNTER.incr_mul()  # x^2 = x*x
        else:
            if isinstance(other, int):
                GLOBAL_COUNTER.incr_i2f()
            GLOBAL_COUNTER.incr_pow()
        return CountedFloat(super().__pow__(other))

    def __rpow__(self, other) -> CountedFloat:
        """other**x"""
        if isinstance(other, int) and other == 2:
            GLOBAL_COUNTER.incr_exp2()
        elif isinstance(other, int) and other == 10:
            GLOBAL_COUNTER.incr_exp10()
        else:
            if isinstance(other, int):
                GLOBAL_COUNTER.incr_i2f()
            GLOBAL_COUNTER.incr_pow()
        return CountedFloat(super().__rpow__(other))


# -------------------------------------------------------------------------
#  monkey-patch some methods of math module
# -------------------------------------------------------------------------
original_math_sqrt = math.sqrt
original_math_cbrt = math.cbrt
original_math_log = math.log
original_math_log2 = math.log2
original_math_log10 = math.log10
original_math_exp = math.exp
original_math_exp2 = math.exp2
original_math_sin = math.sin
original_math_cos = math.cos
original_math_tan = math.tan


def math_sqrt(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_sqrt()
        return CountedFloat(original_math_sqrt(x))
    else:
        return original_math_sqrt(x)


def math_cbrt(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_cbrt()
        return CountedFloat(original_math_cbrt(x))
    else:
        return original_math_cbrt(x)


def math_log(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_log()
        return CountedFloat(original_math_log(x))
    else:
        return original_math_log(x)


def math_log2(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_log2()
        return CountedFloat(original_math_log2(x))
    else:
        return original_math_log2(x)


def math_log10(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_log10()
        return CountedFloat(original_math_log10(x))
    else:
        return original_math_log10(x)


def math_exp(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_exp()
        return CountedFloat(original_math_exp(x))
    else:
        return original_math_exp(x)


def math_exp2(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_exp2()
        return CountedFloat(original_math_exp2(x))
    else:
        return original_math_exp2(x)


def math_pow(x: float, y: float) -> float | CountedFloat:
    return x**y


def math_sin(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_sin()
        return CountedFloat(original_math_sin(x))
    else:
        return original_math_sin(x)


def math_cos(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_cos()
        return CountedFloat(original_math_cos(x))
    else:
        return original_math_cos(x)


def math_tan(x: float) -> float | CountedFloat:
    if isinstance(x, CountedFloat):
        GLOBAL_COUNTER.incr_tan()
        return CountedFloat(original_math_tan(x))
    else:
        return original_math_tan(x)


# override math module methods
math.sqrt = math_sqrt
math.cbrt = math_cbrt
math.log = math_log
math.log2 = math_log2
math.log10 = math_log10
math.exp = math_exp
math.exp2 = math_exp2
math.pow = math_pow
math.sin = math_sin
math.cos = math_cos
math.tan = math_tan
