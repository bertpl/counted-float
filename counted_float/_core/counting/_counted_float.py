from __future__ import annotations

from ._global_counter import GLOBAL_COUNTER


class CountedFloat(float):
    # -------------------------------------------------------------------------
    #  CONSTRUCTOR
    # -------------------------------------------------------------------------
    def __new__(cls, value: float | int):
        if isinstance(value, int):
            GLOBAL_COUNTER.incr_i2f()
        return super().__new__(cls, float(value))

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
        """
        x**other

        Counting heuristic: an `int` operand is taken as evidence of a hardcoded constant in the
        source (ints don't fall out of floating-point computations), so `x**2` counts as MUL —
        the strength reduction (x*x) a compiled port would apply. A float operand may just as well
        be a runtime variable that happens to hold that value, where a port would compile a
        generic pow, so `x**2.0` counts as POW.
        """
        if isinstance(other, int) and other == 2:
            GLOBAL_COUNTER.incr_mul()  # x^2 = x*x
        else:
            if isinstance(other, int):
                GLOBAL_COUNTER.incr_i2f()
            GLOBAL_COUNTER.incr_pow()
        return CountedFloat(super().__pow__(other))

    def __rpow__(self, other) -> CountedFloat:
        """
        other**x

        Same constant-detection heuristic as __pow__, applied to the base: an `int` base 2 or 10
        is taken as a hardcoded constant, counting as EXP2 / EXP10 (the strength reduction a
        compiled port would apply); a float base may be a runtime variable, so it counts as
        generic POW.
        """
        if isinstance(other, int) and other == 2:
            GLOBAL_COUNTER.incr_exp2()
        elif isinstance(other, int) and other == 10:
            GLOBAL_COUNTER.incr_exp10()
        else:
            if isinstance(other, int):
                GLOBAL_COUNTER.incr_i2f()
            GLOBAL_COUNTER.incr_pow()
        return CountedFloat(super().__rpow__(other))
