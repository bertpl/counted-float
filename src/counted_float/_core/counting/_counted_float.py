from __future__ import annotations

from typing import SupportsIndex

from ._global_counter import GLOBAL_COUNTER


def count_pow_with_constant_exponent(exponent: float) -> None:
    """Register the flops a compiled port would execute for ``x ** exponent`` with a constant exponent.

    Constants are folded by value (an int and an equal-valued plain float compile identically):
      - 0, 1                     -> nothing (the expression folds away entirely)
      - 0.5 / -0.5               -> SQRT / SQRT + DIV
      - -1                       -> DIV (reciprocal)
      - integer 2 <= |n| <= 16   -> square-and-multiply MULs (x**3 -> 2 MUL, x**8 -> 3 MUL, ...),
                                    plus one DIV when negative; the |n| <= 16 cutoff keeps the
                                    model honest — beyond it real compilers' powi expansion
                                    varies and a generic POW is a fair stand-in
      - anything else            -> POW
    """
    value = float(exponent)
    if value in (0.0, 1.0):
        return
    if value == 0.5:
        GLOBAL_COUNTER.incr_sqrt()
        return
    if value == -0.5:
        GLOBAL_COUNTER.incr_sqrt()
        GLOBAL_COUNTER.incr_div()
        return
    if value == -1.0:
        GLOBAL_COUNTER.incr_div()
        return
    if value.is_integer() and 2 <= abs(value) <= 16:
        n = abs(int(value))
        n_muls = (n.bit_length() - 1) + bin(n).count("1") - 1  # square-and-multiply cost
        for _ in range(n_muls):
            GLOBAL_COUNTER.incr_mul()
        if value < 0:
            GLOBAL_COUNTER.incr_div()
        return
    GLOBAL_COUNTER.incr_pow()


def count_pow_with_constant_base(base: float) -> None:
    """Register the flops a compiled port would execute for ``base ** x`` with a constant base.

    Constants are folded by value: base 2 -> EXP2, base 10 -> EXP10, anything else -> POW.
    """
    value = float(base)
    if value == 2.0:
        GLOBAL_COUNTER.incr_exp2()
    elif value == 10.0:
        GLOBAL_COUNTER.incr_exp10()
    else:
        GLOBAL_COUNTER.incr_pow()


class CountedFloat(float):
    # numpy counting is an explicit non-goal; refusing numpy's ufunc protocol makes the boundary
    # loud instead of silently uncounted. With the protocol refused, numpy's scalar operators
    # return NotImplemented and Python falls back to this class's reflected methods — np.float64
    # (a plain C double subclassing float) then counts correctly from either side without any
    # numpy semantics being adopted. ndarrays and numpy scalar dtypes that do not subclass float
    # (np.float32, np.int64, ...) raise TypeError instead of producing uncounted results whose
    # type may later recover to CountedFloat and mask the missing flops.
    __array_ufunc__ = None

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
        return f"CountedFloat({float.__repr__(self)})"

    def __hash__(self) -> int:
        return float.__hash__(self)

    # -------------------------------------------------------------------------
    #  OVERLOADED MATH OPERATIONS
    # -------------------------------------------------------------------------
    def __abs__(self) -> CountedFloat:
        """abs(x)."""
        GLOBAL_COUNTER.incr_abs()
        return float.__new__(CountedFloat, float.__abs__(self))

    def __neg__(self) -> CountedFloat:
        """-x."""
        GLOBAL_COUNTER.incr_minus()
        return float.__new__(CountedFloat, float.__neg__(self))

    def __pos__(self) -> CountedFloat:
        """+x.

        Unary plus is the identity; a compiled port emits no instruction, so nothing is counted.
        The type is preserved (returns a CountedFloat) so downstream counting survives.
        """
        return float.__new__(CountedFloat, float.__pos__(self))

    def __eq__(self, other: object) -> bool:
        """x==other or other==x."""
        result = float.__eq__(self, other)
        if result is NotImplemented:
            return NotImplemented  # let Python try the reflected operation; nothing was computed, so nothing counts
        GLOBAL_COUNTER.incr_comp()
        return result

    def __ne__(self, other: object) -> bool:
        """x!=other or other!=x."""
        result = float.__ne__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_comp()
        return result

    def __lt__(self, other: float) -> bool:
        """x<other."""
        result = float.__lt__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_comp()
        return result

    def __le__(self, other: float) -> bool:
        """x<=other."""
        result = float.__le__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_comp()
        return result

    def __gt__(self, other: float) -> bool:
        """x>other."""
        result = float.__gt__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_comp()
        return result

    def __ge__(self, other: float) -> bool:
        """x>=other."""
        result = float.__ge__(self, other)
        if result is NotImplemented:
            return NotImplemented
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

        return float.__round__(self, n)

    def __floor__(self) -> int:
        """math.floor(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return float.__floor__(self)

    def __ceil__(self) -> int:
        """math.ceil(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return float.__ceil__(self)

    def __int__(self) -> int:
        """int(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return float.__int__(self)

    def __trunc__(self) -> int:
        """int(x)."""
        GLOBAL_COUNTER.incr_f2i()
        return float.__trunc__(self)

    def __add__(self, other: float) -> CountedFloat:
        """x+other."""
        result = float.__add__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_add()
        return float.__new__(CountedFloat, result)

    def __radd__(self, other: float) -> CountedFloat:
        """other+x."""
        result = float.__radd__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_add()
        return float.__new__(CountedFloat, result)

    def __sub__(self, other: float) -> CountedFloat:
        """x-other."""
        result = float.__sub__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_sub()
        return float.__new__(CountedFloat, result)

    def __rsub__(self, other: float) -> CountedFloat:
        """other-x."""
        result = float.__rsub__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_sub()
        return float.__new__(CountedFloat, result)

    def __mul__(self, other: float) -> CountedFloat:
        """x*other or other*x."""
        result = float.__mul__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_mul()
        return float.__new__(CountedFloat, result)

    def __rmul__(self, other: float) -> CountedFloat:
        """other*x."""
        result = float.__rmul__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_mul()
        return float.__new__(CountedFloat, result)

    def __truediv__(self, other: float) -> CountedFloat:
        """x/other."""
        result = float.__truediv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        return float.__new__(CountedFloat, result)

    def __rtruediv__(self, other: float) -> CountedFloat:
        """other/x."""
        result = float.__rtruediv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        return float.__new__(CountedFloat, result)

    def __floordiv__(self, other: float) -> CountedFloat:
        """x//y.

        Floored division decomposes into DIV + RND: a compiled port computes x/y and rounds the
        quotient toward -inf, a float->float round (RND / FRINTM / ROUNDSD class), not an F2I.
        """
        result = float.__floordiv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        GLOBAL_COUNTER.incr_rnd()
        return float.__new__(CountedFloat, result)

    def __rfloordiv__(self, other: float) -> CountedFloat:
        """other//x. See __floordiv__ for the DIV + RND decomposition."""
        result = float.__rfloordiv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        GLOBAL_COUNTER.incr_rnd()
        return float.__new__(CountedFloat, result)

    def __mod__(self, other: float) -> CountedFloat:
        """x%y.

        Python's % is the floored remainder r = x - y*floor(x/y), which a compiled port emits as
        DIV + RND (the floor) + MUL + SUB. Distinct from math.fmod, the truncated C remainder.
        """
        result = float.__mod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        GLOBAL_COUNTER.incr_rnd()
        GLOBAL_COUNTER.incr_mul()
        GLOBAL_COUNTER.incr_sub()
        return float.__new__(CountedFloat, result)

    def __rmod__(self, other: float) -> CountedFloat:
        """other%x. See __mod__ for the DIV + RND + MUL + SUB decomposition."""
        result = float.__rmod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        GLOBAL_COUNTER.incr_rnd()
        GLOBAL_COUNTER.incr_mul()
        GLOBAL_COUNTER.incr_sub()
        return float.__new__(CountedFloat, result)

    def __divmod__(self, other: float) -> tuple[CountedFloat, CountedFloat]:
        """divmod(x, y) = (x//y, x%y).

        Quotient and remainder share the DIV + RND (the floor); the remainder adds MUL + SUB, so
        divmod counts DIV + RND + MUL + SUB — the same as a lone %, since the // part is shared.
        """
        result = float.__divmod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        GLOBAL_COUNTER.incr_rnd()
        GLOBAL_COUNTER.incr_mul()
        GLOBAL_COUNTER.incr_sub()
        quotient, remainder = result
        return float.__new__(CountedFloat, quotient), float.__new__(CountedFloat, remainder)

    def __rdivmod__(self, other: float) -> tuple[CountedFloat, CountedFloat]:
        """divmod(other, x). See __divmod__ for the DIV + RND + MUL + SUB decomposition."""
        result = float.__rdivmod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        GLOBAL_COUNTER.incr_div()
        GLOBAL_COUNTER.incr_rnd()
        GLOBAL_COUNTER.incr_mul()
        GLOBAL_COUNTER.incr_sub()
        quotient, remainder = result
        return float.__new__(CountedFloat, quotient), float.__new__(CountedFloat, remainder)

    def __pow__(self, other: float) -> CountedFloat:  # ty: ignore[invalid-method-override] -- no `mod` param; float.__pow__'s mod is None-only and unused here
        """x**other.

        A constant (non-CountedFloat) exponent enables the strength reduction a compiled port
        would apply — see count_pow_with_constant_exponent for the value-based rules (`x**2` ->
        MUL, `x**0.5` -> SQRT, `x**-1` -> DIV, small int exponents -> their multiply chain).
        Per the counting model, constant operands never add an I2F conversion.

        A negative base with a fractional exponent yields a complex result (as for plain float);
        complex values fall outside the counting model, so nothing is counted and the result is
        returned unwrapped.
        """
        result = float.__pow__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if not isinstance(result, float):
            return result
        if isinstance(other, CountedFloat):
            GLOBAL_COUNTER.incr_pow()  # genuinely runtime exponent
        else:
            count_pow_with_constant_exponent(other)
        return float.__new__(CountedFloat, result)

    def __rpow__(self, other: float) -> CountedFloat:  # ty: ignore[invalid-method-override] -- no `mod` param; float.__rpow__'s mod is None-only and unused here
        """other**x.

        Strength reduction on the base, as in __pow__: a constant (non-CountedFloat) base 2 or
        10 counts as EXP2 / EXP10 (what a compiled port would emit, folding constants by value);
        any other base counts a generic POW. Per the counting model, constant operands never add
        an I2F conversion.

        A negative base with a fractional exponent yields a complex result (as for plain float);
        complex values fall outside the counting model, so nothing is counted and the result is
        returned unwrapped.
        """
        result = float.__rpow__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if not isinstance(result, float):
            return result
        if isinstance(other, CountedFloat):
            GLOBAL_COUNTER.incr_pow()  # genuinely runtime base
        else:
            count_pow_with_constant_base(other)
        return float.__new__(CountedFloat, result)
