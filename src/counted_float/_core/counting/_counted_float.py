from __future__ import annotations

import operator
from math import frexp as _frexp  # the raw builtin: math.frexp may later carry a reporting wrapper
from typing import TYPE_CHECKING, SupportsIndex

from ._thread_counter import _TLS, _create_thread_state

if TYPE_CHECKING:
    from ._thread_counter import CountsTarget


def count_pow_with_constant_exponent(exponent: float) -> None:
    """Register the flops a compiled port would execute for ``x ** exponent`` with a constant exponent.

    Constants are folded by value (an int and an equal-valued plain float compile identically):
      - 0, 1                     -> nothing (the expression folds away entirely)
      - 0.5 / -0.5               -> SQRT / SQRT + DIV
      - -1                       -> DIV (reciprocal)
      - integer 2 <= |n| <= 16   -> square-and-multiply MULs (x**3 -> 2 MUL, x**8 -> 3 MUL, ...),
                                    plus one DIV when negative; the |n| <= 16 cutoff keeps the
                                    model honest — beyond it real compilers' powi expansion
                                    varies and a generic POW is a fair stand-in.  The chain is a
                                    source-level porting decision, priced as written — not a
                                    toolchain transformation needing bit-identity to libm pow;
                                    see the constant-exponent rule in docs/cost_model.md
      - anything else            -> POW
    """
    value = float(exponent)
    if value in (0.0, 1.0):
        return
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    if value == 0.5:
        cnt.note("const exponent 0.5 -> sqrt")
        cnt.SQRT += 1
        return
    if value == -0.5:
        cnt.note("const exponent -0.5 -> sqrt + reciprocal")
        cnt.SQRT += 1
        cnt.DIV += 1
        return
    if value == -1.0:
        cnt.note("const exponent -1 -> reciprocal")
        cnt.DIV += 1
        return
    if value.is_integer() and 2 <= abs(value) <= 16:
        n = abs(int(value))
        n_muls = (n.bit_length() - 1) + bin(n).count("1") - 1  # square-and-multiply cost
        # a constant string, like every rationale: the counting sites hand one over on every call,
        # so building one costs even the runs that never render it
        cnt.note("const exponent -> square-and-multiply")
        cnt.MUL += n_muls
        if value < 0:
            cnt.note("negative exponent -> reciprocal")
            cnt.DIV += 1
        return
    cnt.POW += 1


def count_div_with_constant_divisor(divisor: float) -> None:
    """Register the flops a compiled port would execute for ``x / divisor`` with a constant divisor.

    Constants are folded by value (an int and an equal-valued plain float compile identically):
    a divisor of 1 counts nothing (``x / 1.0`` folds away entirely — a compiled port emits no
    instruction, mirroring ``x ** 1``), and any other power-of-two divisor with a finite
    reciprocal counts MUL — for exactly those divisors ``x * (1/c)`` is bit-identical to
    ``x / c``, so a standard-C compiler applies the reciprocal fold at plain ``-O2``. Every
    other divisor counts DIV.
    """
    if divisor == 1.0:
        return
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    mantissa, exponent = _frexp(divisor)
    # power of two iff the mantissa is exactly +/-0.5; the divisor is then 2**(exponent-1), whose
    # reciprocal 2**(1-exponent) stays finite iff exponent >= -1022 (below that it overflows and
    # the fold would not be value-preserving)
    if mantissa in (0.5, -0.5) and exponent >= -1022:
        cnt.note("power-of-two constant divisor -> reciprocal multiply")
        cnt.MUL += 1
    else:
        cnt.DIV += 1


def count_pow_with_constant_base(base: float) -> None:
    """Register the flops a compiled port would execute for ``base ** x`` with a constant base.

    Constants are folded by value: base 2 -> EXP2, base 10 -> EXP10, anything else -> POW.
    """
    value = float(base)
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    if value == 2.0:
        cnt.note("const base 2 -> exp2")
        cnt.EXP2 += 1
    elif value == 10.0:
        cnt.note("const base 10 -> exp10")
        cnt.EXP10 += 1
    else:
        cnt.POW += 1


class CountedFloat(float):
    # a drop-in float, enforced: empty slots suppress the per-instance __dict__ a slotless
    # subclass would carry, so attribute assignment and weak references are refused with the
    # exact errors plain float gives (and instances shed 16 of their 32 bytes over plain float)
    __slots__ = ()

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
            try:
                _TLS.flop_counts.I2F += 1
            except AttributeError:  # first counted op on this thread
                _create_thread_state().I2F += 1
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
        try:
            _TLS.flop_counts.ABS += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ABS += 1
        return float.__new__(CountedFloat, float.__abs__(self))

    def __neg__(self) -> CountedFloat:
        """-x."""
        try:
            _TLS.flop_counts.MINUS += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MINUS += 1
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
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result

    def __ne__(self, other: object) -> bool:
        """x!=other or other!=x."""
        result = float.__ne__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result

    def __lt__(self, other: float) -> bool:
        """x<other."""
        result = float.__lt__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result

    def __le__(self, other: float) -> bool:
        """x<=other."""
        result = float.__le__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result

    def __gt__(self, other: float) -> bool:
        """x>other."""
        result = float.__gt__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result

    def __ge__(self, other: float) -> bool:
        """x>=other."""
        result = float.__ge__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.COMP += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().COMP += 1
        return result

    def __round__(  # ty: ignore[invalid-method-override] -- float's stub narrows return per overload; this is the union
        self, n: SupportsIndex | None = None
    ) -> int | float:
        """Round to n decimal places, i.e. round(x, n).

        n = None -> round to nearest integer and return int (F2I)
        n = 0    -> round to nearest integer and return float (RND)
        n != 0   -> round to n decimal places and return float: a compiled port scales into
                    the digit position, rounds, and scales back -- MUL + RND + DIV. The
                    unscale is a true divide (the scale factor is a power of ten, whose
                    reciprocal is not exact), so no reciprocal fold applies. Stated gap: the
                    port price knowingly omits the correctly-rounded decimal machinery
                    CPython itself runs (David Gay's algorithm), which has no fixed
                    instruction cost to price.
        """
        if n is None:
            try:
                _TLS.flop_counts.F2I += 1  # will round and return int
            except AttributeError:  # first counted op on this thread
                _create_thread_state().F2I += 1
        elif operator.index(n) == 0:
            try:
                _TLS.flop_counts.RND += 1  # will round and return float
            except AttributeError:  # first counted op on this thread
                _create_thread_state().RND += 1
        else:
            try:
                cnt: CountsTarget = _TLS.flop_counts
            except AttributeError:  # first counted op on this thread
                cnt: CountsTarget = _create_thread_state()
            cnt.note("nonzero ndigits -> scale, round, unscale")
            cnt.MUL += 1
            cnt.RND += 1
            cnt.DIV += 1

        return float.__round__(self, n)

    def __floor__(self) -> int:
        """math.floor(x)."""
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return float.__floor__(self)

    def __ceil__(self) -> int:
        """math.ceil(x)."""
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return float.__ceil__(self)

    def __int__(self) -> int:
        """int(x)."""
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return float.__int__(self)

    def __trunc__(self) -> int:
        """int(x)."""
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return float.__trunc__(self)

    def __add__(self, other: float) -> CountedFloat:
        """x+other."""
        result = float.__add__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.ADD += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ADD += 1
        return float.__new__(CountedFloat, result)

    def __radd__(self, other: float) -> CountedFloat:
        """other+x."""
        result = float.__radd__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.ADD += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ADD += 1
        return float.__new__(CountedFloat, result)

    def __sub__(self, other: float) -> CountedFloat:
        """x-other."""
        result = float.__sub__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.SUB += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().SUB += 1
        return float.__new__(CountedFloat, result)

    def __rsub__(self, other: float) -> CountedFloat:
        """other-x."""
        result = float.__rsub__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.SUB += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().SUB += 1
        return float.__new__(CountedFloat, result)

    def __mul__(self, other: float) -> CountedFloat:
        """x*other or other*x."""
        result = float.__mul__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.MUL += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, result)

    def __rmul__(self, other: float) -> CountedFloat:
        """other*x."""
        result = float.__rmul__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.MUL += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, result)

    def __truediv__(self, other: float) -> CountedFloat:
        """x/other.

        A constant (non-CountedFloat) divisor enables the folds a compiled port applies — see
        count_div_with_constant_divisor: a divisor of 1 counts nothing, any other power-of-two
        constant divisor with a finite reciprocal counts MUL, everything else counts DIV.
        """
        result = float.__truediv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if isinstance(other, CountedFloat):
            try:
                _TLS.flop_counts.DIV += 1  # genuinely runtime divisor
            except AttributeError:  # first counted op on this thread
                _create_thread_state().DIV += 1
        else:
            count_div_with_constant_divisor(other)
        return float.__new__(CountedFloat, result)

    def __rtruediv__(self, other: float) -> CountedFloat:
        """other/x. The divisor is this CountedFloat — dynamic, so always DIV (no fold applies)."""
        result = float.__rtruediv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            _TLS.flop_counts.DIV += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().DIV += 1
        return float.__new__(CountedFloat, result)

    def __floordiv__(self, other: float) -> CountedFloat:
        """x//y.

        Floored division decomposes into DIV + RND: a compiled port computes x/y and rounds the
        quotient toward -inf, a float->float round (RND / FRINTM / ROUNDSD class), not an F2I.
        """
        result = float.__floordiv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.DIV += 1
        cnt.RND += 1
        return float.__new__(CountedFloat, result)

    def __rfloordiv__(self, other: float) -> CountedFloat:
        """other//x. See __floordiv__ for the DIV + RND decomposition."""
        result = float.__rfloordiv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.DIV += 1
        cnt.RND += 1
        return float.__new__(CountedFloat, result)

    def __mod__(self, other: float) -> CountedFloat:
        """x%y.

        Python's % is the floored remainder r = x - y*floor(x/y), which a compiled port emits as
        DIV + RND (the floor) + MUL + SUB. Distinct from math.fmod, the truncated C remainder.
        """
        result = float.__mod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.DIV += 1
        cnt.RND += 1
        cnt.MUL += 1
        cnt.SUB += 1
        return float.__new__(CountedFloat, result)

    def __rmod__(self, other: float) -> CountedFloat:
        """other%x. See __mod__ for the DIV + RND + MUL + SUB decomposition."""
        result = float.__rmod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.DIV += 1
        cnt.RND += 1
        cnt.MUL += 1
        cnt.SUB += 1
        return float.__new__(CountedFloat, result)

    def __divmod__(self, other: float) -> tuple[CountedFloat, CountedFloat]:
        """divmod(x, y) = (x//y, x%y).

        Quotient and remainder share the DIV + RND (the floor); the remainder adds MUL + SUB, so
        divmod counts DIV + RND + MUL + SUB — the same as a lone %, since the // part is shared.
        """
        result = float.__divmod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.DIV += 1
        cnt.RND += 1
        cnt.MUL += 1
        cnt.SUB += 1
        quotient, remainder = result
        return float.__new__(CountedFloat, quotient), float.__new__(CountedFloat, remainder)

    def __rdivmod__(self, other: float) -> tuple[CountedFloat, CountedFloat]:
        """divmod(other, x). See __divmod__ for the DIV + RND + MUL + SUB decomposition."""
        result = float.__rdivmod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.DIV += 1
        cnt.RND += 1
        cnt.MUL += 1
        cnt.SUB += 1
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
            try:
                _TLS.flop_counts.POW += 1  # genuinely runtime exponent
            except AttributeError:  # first counted op on this thread
                _create_thread_state().POW += 1
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
            try:
                _TLS.flop_counts.POW += 1  # genuinely runtime base
            except AttributeError:  # first counted op on this thread
                _create_thread_state().POW += 1
        else:
            count_pow_with_constant_base(other)
        return float.__new__(CountedFloat, result)
