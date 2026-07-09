from __future__ import annotations

from typing import SupportsIndex

from ._global_counter import GLOBAL_COUNTER


class CountedFloat(float):
    # -------------------------------------------------------------------------
    #  CONSTRUCTOR
    # -------------------------------------------------------------------------
    def __new__(cls, value: float | int) -> CountedFloat:
        if isinstance(value, int):
            GLOBAL_COUNTER.incr_i2f()
        return super().__new__(cls, float(value))

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"CountedFloat({super().__repr__()})"

    def __hash__(self) -> int:
        return super().__hash__()

    # -------------------------------------------------------------------------
    #  OVERLOADED MATH OPERATIONS
    # -------------------------------------------------------------------------
    def __abs__(self) -> CountedFloat:
        """abs(x)."""
        GLOBAL_COUNTER.incr_abs()
        return CountedFloat(super().__abs__())

    def __neg__(self) -> CountedFloat:
        """-x."""
        GLOBAL_COUNTER.incr_minus()
        return CountedFloat(super().__neg__())

    def __eq__(self, other: object) -> bool:
        """x==other or other==x."""
        result = super().__eq__(other)
        if result is NotImplemented:
            return NotImplemented  # let Python try the reflected operation; nothing was computed, so nothing counts
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return result

    def __ne__(self, other: object) -> bool:
        """x!=other or other!=x."""
        result = super().__ne__(other)
        if result is NotImplemented:
            return NotImplemented
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return result

    def __lt__(self, other: float) -> bool:
        """x<other."""
        result = super().__lt__(other)
        if result is NotImplemented:
            return NotImplemented
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return result

    def __le__(self, other: float) -> bool:
        """x<=other."""
        result = super().__le__(other)
        if result is NotImplemented:
            return NotImplemented
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return result

    def __gt__(self, other: float) -> bool:
        """x>other."""
        result = super().__gt__(other)
        if result is NotImplemented:
            return NotImplemented
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return result

    def __ge__(self, other: float) -> bool:
        """x>=other."""
        result = super().__ge__(other)
        if result is NotImplemented:
            return NotImplemented
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        GLOBAL_COUNTER.incr_comp()
        return result

    def __round__(  # ty: ignore[invalid-method-override] -- float's stub narrows return per overload; this is the union
        self, n: SupportsIndex | None = None
    ) -> int | float:
        """Round to n decimal places, i.e. round(x, n).

        n = None -> round to nearest integer and return int
        n = 0    -> round to nearest integer and return float
        n > 0    -> round to n decimal places and return float.
        """
        if n is None:
            GLOBAL_COUNTER.incr_f2i()  # will round and return int
        else:
            GLOBAL_COUNTER.incr_rnd()  # will round and return float

        return super().__round__(n)

    def __floor__(self) -> int:
        """math.floor(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return super().__floor__()

    def __ceil__(self) -> int:
        """math.ceil(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return super().__ceil__()

    def __int__(self) -> int:
        """int(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return super().__int__()

    def __trunc__(self) -> int:
        """int(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return super().__trunc__()

    def __add__(self, other: float) -> CountedFloat:
        """x+other."""
        result = super().__add__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_add()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __radd__(self, other: float) -> CountedFloat:
        """other+x."""
        result = super().__radd__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_add()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __sub__(self, other: float) -> CountedFloat:
        """x-other."""
        result = super().__sub__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_sub()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __rsub__(self, other: float) -> CountedFloat:
        """other-x."""
        result = super().__rsub__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_sub()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __mul__(self, other: float) -> CountedFloat:
        """x*other or other*x."""
        result = super().__mul__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_mul()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __rmul__(self, other: float) -> CountedFloat:
        """other*x."""
        result = super().__rmul__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_mul()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __truediv__(self, other: float) -> CountedFloat:
        """x/other."""
        result = super().__truediv__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __rtruediv__(self, other: float) -> CountedFloat:
        """other/x."""
        result = super().__rtruediv__(other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        if isinstance(other, int):
            GLOBAL_COUNTER.incr_i2f()
        return CountedFloat(result)

    def __pow__(self, other: float) -> CountedFloat:  # ty: ignore[invalid-method-override] -- no `mod` param; float.__pow__'s mod is None-only and unused here
        """x**other.

        Counting heuristic: an `int` operand is taken as evidence of a hardcoded constant in the
        source (ints don't fall out of floating-point computations), so `x**2` counts as MUL —
        the strength reduction (x*x) a compiled port would apply. A float operand may just as well
        be a runtime variable that happens to hold that value, where a port would compile a
        generic pow, so `x**2.0` counts as POW.

        A negative base with a fractional exponent yields a complex result (as for plain float);
        complex values fall outside the counting model, so nothing is counted and the result is
        returned unwrapped.
        """
        result = super().__pow__(other)
        if result is NotImplemented:
            return NotImplemented
        if not isinstance(result, float):
            return result
        if isinstance(other, int) and other == 2:
            GLOBAL_COUNTER.incr_mul()  # x^2 = x*x
        else:
            if isinstance(other, int):
                GLOBAL_COUNTER.incr_i2f()
            GLOBAL_COUNTER.incr_pow()
        return CountedFloat(result)

    def __rpow__(self, other: float) -> CountedFloat:  # ty: ignore[invalid-method-override] -- no `mod` param; float.__rpow__'s mod is None-only and unused here
        """other**x.

        Same constant-detection heuristic as __pow__, applied to the base: an `int` base 2 or 10
        is taken as a hardcoded constant, counting as EXP2 / EXP10 (the strength reduction a
        compiled port would apply); a float base may be a runtime variable, so it counts as
        generic POW.

        A negative base with a fractional exponent yields a complex result (as for plain float);
        complex values fall outside the counting model, so nothing is counted and the result is
        returned unwrapped.
        """
        result = super().__rpow__(other)
        if result is NotImplemented:
            return NotImplemented
        if not isinstance(result, float):
            return result
        if isinstance(other, int) and other == 2:
            GLOBAL_COUNTER.incr_exp2()
        elif isinstance(other, int) and other == 10:
            GLOBAL_COUNTER.incr_exp10()
        else:
            if isinstance(other, int):
                GLOBAL_COUNTER.incr_i2f()
            GLOBAL_COUNTER.incr_pow()
        return CountedFloat(result)
