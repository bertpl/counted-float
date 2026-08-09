from __future__ import annotations

import operator
from math import copysign as _copysign  # the raw builtin: math.copysign is patched inside contexts
from math import frexp as _frexp  # the raw builtin: math.frexp may later carry a reporting wrapper
from typing import TYPE_CHECKING, SupportsIndex, final

from ._thread_counter import _TLS, _create_thread_state, thread_is_reporting
from .verbosity import warn_uncounted_call

if TYPE_CHECKING:
    from ._thread_counter import CountsTarget


def count_pow_with_constant_exponent(exponent: float) -> None:
    """Register the flops a compiled port would execute for ``x ** exponent`` with a constant exponent.

    Constants are folded by value (an int and an equal-valued plain float compile identically):
      - 0                        -> nothing (IEEE 754 and C99 define pow(x, 0) as 1.0 for every
                                    x, nan and infinities included, so the port ships the
                                    constant -- __pow__ returns it plain)
      - 1                        -> nothing (the expression folds away to x itself, still counted)
      - 0.5 / -0.5               -> SQRT / SQRT + DIV
      - -1                       -> DIV (reciprocal)
      - integer 2 <= |n| <= 16   -> square-and-multiply MULs (x**3 -> 2 MUL, x**8 -> 3 MUL, ...),
                                    plus one DIV when negative; the |n| <= 16 cutoff keeps the
                                    model honest — beyond it real compilers' powi expansion
                                    varies and a generic POW is a fair stand-in.  The chain is a
                                    source-level porting decision, priced as written — not a
                                    toolchain transformation needing bit-identity to libm pow;
                                    see exponent-chain-bound in docs/cost_model_interpretations.md
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
    instruction, mirroring ``x ** 1``), and any other power-of-two divisor of either sign with a
    finite reciprocal counts MUL — for exactly those divisors ``x * (1/c)`` is bit-identical to
    ``x / c``, so a standard-C compiler applies the reciprocal fold at plain ``-O2``. Every
    other divisor counts DIV.
    """
    if divisor == 1.0:
        return
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    if divisor == -1.0:
        # x / -1.0 is exactly -x, so the port emits a bare sign flip -- the reciprocal-multiply
        # branch below would otherwise price it as MUL (cost-model rule 1)
        cnt.note("constant divisor -1.0 -> sign flip")
        cnt.MINUS += 1
        return
    mantissa, exponent = _frexp(divisor)
    # power of two iff the mantissa is exactly +/-0.5; the divisor is then 2**(exponent-1), whose
    # reciprocal 2**(1-exponent) stays finite iff exponent >= -1022 (below that it overflows and
    # the fold would not be value-preserving)
    if mantissa in (0.5, -0.5) and exponent >= -1022:
        cnt.note("power-of-two constant divisor -> reciprocal multiply")
        cnt.MUL += 1
    else:
        cnt.DIV += 1


def count_mul_with_identity_multiplier(multiplier: float) -> None:
    """Register the flops for ``x * multiplier`` where the constant is ``1.0`` or ``-1.0``.

    The sign-exact identity folds of cost-model rule 1: multiplying by constant 1 folds away
    entirely (a compiled port emits no instruction), multiplying by constant -1 reduces to a bare
    sign flip and counts MINUS. Callers pre-check the multiplier, so any other value is a bug.
    """
    if multiplier == 1.0:
        return
    try:
        cnt: CountsTarget = _TLS.flop_counts
    except AttributeError:  # first counted op on this thread
        cnt: CountsTarget = _create_thread_state()
    cnt.note("constant multiplier -1.0 -> sign flip")
    cnt.MINUS += 1


def count_pow_with_constant_base(base: float) -> None:
    """Register the flops a compiled port would execute for ``base ** x`` with a constant base.

    Constants are folded by value: base 2 -> EXP2, base 10 -> EXP10, anything else -> POW.

    Base 1 never arrives here: IEEE 754 and C99 make pow(1, y) 1.0 for every y (nan included),
    so the callers return that constant as a plain float without counting, the way __pow__
    handles a constant exponent of 0.
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


@final
class CountedFloat(float):
    # a drop-in float, enforced: empty slots suppress the per-instance __dict__ a slotless
    # subclass would carry, so attribute assignment and weak references are refused with the
    # exact errors plain float gives (and instances shed 16 of their 32 bytes over plain float)
    __slots__ = ()

    # subclassing is consciously unsupported, sealed at runtime and not only for type checkers,
    # because that is what buys the hot-path optimizations below: with no subtype possible, the
    # operand tests can ask `type(other) is CountedFloat` instead of isinstance (about twice as
    # cheap for a plain-float operand, which is the constant-folding path every operator runs),
    # and every result can be constructed as a CountedFloat by name rather than from the
    # operand's type
    def __init_subclass__(cls, **kwargs: object) -> None:
        """Refuse subclass creation, which the hot-path design deliberately rules out."""
        raise TypeError(
            "CountedFloat does not support subclassing: its operators trade that away for exact-type "
            "operand tests on the counting hot path.  Hold a CountedFloat in your own type instead."
        )

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
        """Construct from a numeric source, counting I2F for int inputs.

        The source matrix is the counting model's entry contract: an int (bool included) counts
        I2F, the port's int->double conversion instruction; a float source costs nothing (no
        conversion exists); Decimal and Fraction convert uncounted -- their conversion has no
        FlopType, a stated gap, since non-float numeric types sit outside the model's scope.
        Numeric-source construction is the supported contract: counted code converts numbers,
        it does not parse them. Strings happen to work (the delegation to ``float(value)``
        accepts them) but that is incidental, not part of the contract -- hence the annotation;
        like fromhex, the parse is uncounted.
        """
        instance = super().__new__(cls, float(value))  # compute first: an oversized int raises before counting
        if isinstance(value, int):
            try:
                _TLS.flop_counts.I2F += 1
            except AttributeError:  # first counted op on this thread
                _create_thread_state().I2F += 1
        return instance

    def __repr__(self) -> str:
        """The loud counted-value repr — the single presentation mechanism.

        float defines no __str__ of its own, so str(x), print(x), f"{x}" and format(x, "") all
        land here, through object.__str__ and float.__format__'s empty-spec fast path. Loud on
        purpose: whether a value silently fell out of the counting system is this library's
        central hazard, and the repr is the zero-cost place it shows. Any non-empty format spec
        (even a bare alignment) formats the plain value instead.
        """
        return f"CountedFloat({float.__repr__(self)})"

    def __hash__(self) -> int:
        return float.__hash__(self)

    # -------------------------------------------------------------------------
    #  FLOAT-SURFACE MEMBERS
    # -------------------------------------------------------------------------
    # .imag deliberately stays inherited: it is +0.0 for every receiver (signs and nan payloads
    # included), so it is a compile-time constant of the port and the plain-float return is the
    # correct one -- see the cost model's constant-result convention. The two receiver-dependent
    # members of the complex protocol are overridden below.
    @property
    def real(self) -> CountedFloat:
        """The real part: the receiver itself, bit-identical (the complex protocol on a real).

        A compiled port emits no instruction, so nothing is counted; the type is preserved so
        downstream counting survives, as for __pos__. Returns self rather than the neighbors'
        fresh-construction idiom: the class is final and immutable, so identity is unobservable
        and an equal copy buys nothing.
        """
        return self

    def conjugate(self) -> CountedFloat:
        """The complex conjugate: the receiver itself, bit-identical for every real value.

        Same contract as `real`: no instruction in the port, nothing counted, type preserved.
        """
        return self

    def is_integer(self) -> bool:
        """Whether the value is integral, counted as RND + COMP.

        CPython computes `floor(x) == x` with C's double->double floor (Objects/floatobject.c,
        float_is_integer), so the port pays one float->float round and one compare -- the price
        of the counted spelling `x // 1.0 == x`, and RND rather than F2I because no int ever
        materializes. The non-finite early return (False, nothing computed) is a regime fast
        path; the price is charged unconditionally, per the cost model's input-range rules.
        """
        result = float.is_integer(self)
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        cnt.RND += 1
        cnt.COMP += 1
        return result

    def as_integer_ratio(self) -> tuple[int, int]:
        """The exact integer ratio, uncounted but reported at WARNING verbosity.

        The port's extraction is a bit-field read plus an integer shift -- integer-domain work
        the model prices nowhere -- so nothing is counted. But `n / d` on the result silently
        resumes float arithmetic at zero flops, the same re-entry math.frexp reports, so the
        call is surfaced through the same channel. Unlike the math patches this override is
        permanently installed; the method is cold and the reporting test is one TLS read.
        """
        if thread_is_reporting():
            warn_uncounted_call("float.as_integer_ratio", "its integer parts re-enter float math uncounted")
        return float.as_integer_ratio(self)

    # -------------------------------------------------------------------------
    #  OVERLOADED MATH OPERATIONS
    # -------------------------------------------------------------------------
    def __abs__(self) -> CountedFloat:
        """abs(x)."""
        result = float.__abs__(self)
        try:
            _TLS.flop_counts.ABS += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ABS += 1
        return float.__new__(CountedFloat, result)

    def __neg__(self) -> CountedFloat:
        """-x."""
        result = float.__neg__(self)
        try:
            _TLS.flop_counts.MINUS += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MINUS += 1
        return float.__new__(CountedFloat, result)

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
        n = 0    -> round to nearest integer and return CountedFloat (RND)
        n != 0   -> round to n decimal places and return CountedFloat: a compiled port scales
                    into the digit position, rounds, and scales back -- MUL + RND + DIV. The
                    unscale is a true divide (the scale factor is a power of ten, whose
                    reciprocal is not exact), so no reciprocal fold applies. Stated gap: the
                    port price knowingly omits the correctly-rounded decimal machinery
                    CPython itself runs (David Gay's algorithm), which has no fixed
                    instruction cost to price.

        The float-returning overloads re-wrap: the result depends on the receiver and carries
        counted work, so a plain-float return would silently stop all downstream counting.
        """
        result = float.__round__(self, n)  # compute first: round(inf/nan) with n=None raises (F2I) before counting
        if n is None:
            try:
                _TLS.flop_counts.F2I += 1  # rounded and returned int
            except AttributeError:  # first counted op on this thread
                _create_thread_state().F2I += 1
            return result
        if operator.index(n) == 0:
            try:
                _TLS.flop_counts.RND += 1  # rounded and returned float
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

        return float.__new__(CountedFloat, result)

    def __floor__(self) -> int:
        """math.floor(x)."""
        result = float.__floor__(self)  # compute first: floor(inf/nan) raises before counting
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return result

    def __ceil__(self) -> int:
        """math.ceil(x)."""
        result = float.__ceil__(self)  # compute first: ceil(inf/nan) raises before counting
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return result

    def __int__(self) -> int:
        """int(x)."""
        result = float.__int__(self)  # compute first: int(inf/nan) raises before counting
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return result

    def __trunc__(self) -> int:
        """int(x)."""
        result = float.__trunc__(self)  # compute first: trunc(inf/nan) raises before counting
        try:
            _TLS.flop_counts.F2I += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().F2I += 1
        return result

    def __add__(self, other: float) -> CountedFloat:
        """x+other.

        A constant (non-CountedFloat) addend of -0.0 folds away: x + (-0.0) is x for every x,
        so a compiled port emits nothing (cost-model rule 1). A +0.0 addend does NOT fold
        ((-0.0) + 0.0 is +0.0) and counts ADD like any other.
        """
        result = float.__add__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if type(other) is not CountedFloat and other == 0.0 and _copysign(1.0, other) < 0.0:
            return float.__new__(CountedFloat, result)  # constant addend -0.0 -> folds away
        try:
            _TLS.flop_counts.ADD += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ADD += 1
        return float.__new__(CountedFloat, result)

    def __radd__(self, other: float) -> CountedFloat:
        """other+x. See __add__ for the -0.0 constant-addend fold (addition commutes)."""
        result = float.__radd__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if type(other) is not CountedFloat and other == 0.0 and _copysign(1.0, other) < 0.0:
            return float.__new__(CountedFloat, result)  # constant addend -0.0 -> folds away
        try:
            _TLS.flop_counts.ADD += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().ADD += 1
        return float.__new__(CountedFloat, result)

    def __sub__(self, other: float) -> CountedFloat:
        """x-other.

        A constant (non-CountedFloat) subtrahend of +0.0 folds away: x - 0.0 is x for every x
        (cost-model rule 1). A -0.0 subtrahend does NOT fold (x - (-0.0) is x + 0.0) and
        counts SUB like any other.
        """
        result = float.__sub__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if type(other) is not CountedFloat and other == 0.0 and _copysign(1.0, other) > 0.0:
            return float.__new__(CountedFloat, result)  # constant subtrahend +0.0 -> folds away
        try:
            _TLS.flop_counts.SUB += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().SUB += 1
        return float.__new__(CountedFloat, result)

    def __rsub__(self, other: float) -> CountedFloat:
        """other-x.

        A constant minuend of -0.0 is a bare sign flip: (-0.0) - x is exactly -x for every x,
        so it counts MINUS (cost-model rule 1). A +0.0 minuend is NOT a sign flip
        (0.0 - 0.0 is +0.0, where -x would be -0.0) and counts SUB like any other.
        """
        result = float.__rsub__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if type(other) is not CountedFloat and other == 0.0 and _copysign(1.0, other) < 0.0:
            try:
                cnt: CountsTarget = _TLS.flop_counts
            except AttributeError:  # first counted op on this thread
                cnt: CountsTarget = _create_thread_state()
            cnt.note("constant minuend -0.0 -> sign flip")
            cnt.MINUS += 1
            return float.__new__(CountedFloat, result)
        try:
            _TLS.flop_counts.SUB += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().SUB += 1
        return float.__new__(CountedFloat, result)

    def __mul__(self, other: float) -> CountedFloat:
        """x*other.

        A constant (non-CountedFloat) multiplier of 1.0 folds away and -1.0 is a bare sign
        flip counting MINUS — see count_mul_with_identity_multiplier (cost-model rule 1).
        Every other multiplier counts MUL.
        """
        result = float.__mul__(self, other)
        if result is NotImplemented:
            return NotImplemented
        # two compares: no set on the hot path.  The type test short-circuits ahead of them, and the
        # class is sealed, so the compares only ever see a plain float - never a counted __eq__,
        # which would register a COMP the user never wrote
        if type(other) is not CountedFloat and (other == 1.0 or other == -1.0):
            count_mul_with_identity_multiplier(other)
            return float.__new__(CountedFloat, result)
        try:
            _TLS.flop_counts.MUL += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, result)

    def __rmul__(self, other: float) -> CountedFloat:
        """other*x. See __mul__ for the identity-multiplier folds (multiplication commutes)."""
        result = float.__rmul__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if type(other) is not CountedFloat and (other == 1.0 or other == -1.0):  # two compares: no set on the hot path
            count_mul_with_identity_multiplier(other)
            return float.__new__(CountedFloat, result)
        try:
            _TLS.flop_counts.MUL += 1
        except AttributeError:  # first counted op on this thread
            _create_thread_state().MUL += 1
        return float.__new__(CountedFloat, result)

    def __truediv__(self, other: float) -> CountedFloat:
        """x/other.

        A constant (non-CountedFloat) divisor enables the folds a compiled port applies — see
        count_div_with_constant_divisor: a divisor of 1 counts nothing, any other power-of-two
        constant divisor of either sign with a finite reciprocal counts MUL, everything else
        counts DIV.
        """
        result = float.__truediv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if type(other) is CountedFloat:
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
        A constant divisor routes the division step through the same folds as a bare `/`
        (count_div_with_constant_divisor; rule 1 - reciprocal-exactness-bound).
        """
        result = float.__floordiv__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if type(other) is CountedFloat:
            try:
                cnt: CountsTarget = _TLS.flop_counts
            except AttributeError:  # first counted op on this thread
                cnt: CountsTarget = _create_thread_state()
            cnt.DIV += 1
            cnt.RND += 1
        else:
            count_div_with_constant_divisor(other)
            try:
                _TLS.flop_counts.RND += 1
            except AttributeError:  # first counted op on this thread
                _create_thread_state().RND += 1
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
        A constant divisor routes the division step through the same folds as a bare `/`
        (count_div_with_constant_divisor; rule 1 - reciprocal-exactness-bound) — and it is also the constant
        factor of the y*floor(...) multiply, so the identity folds apply there too: a divisor
        of 1.0 drops that multiply, -1.0 makes it a bare sign flip (MINUS). Any other constant
        keeps it a genuine MUL: the floor factor is freshly computed, never foldable.
        """
        result = float.__mod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        if type(other) is CountedFloat:
            cnt.DIV += 1
            cnt.MUL += 1
        else:
            count_div_with_constant_divisor(other)
            if other == 1.0 or other == -1.0:
                count_mul_with_identity_multiplier(other)
            else:
                cnt.MUL += 1
        cnt.RND += 1
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
        A constant divisor routes the shared division step through the same folds as a bare `/`
        (count_div_with_constant_divisor; rule 1 - reciprocal-exactness-bound), and folds the remainder's
        y*floor(...) multiply for a ±1.0 divisor the way % does.
        """
        result = float.__divmod__(self, other)
        if result is NotImplemented:
            return NotImplemented
        try:
            cnt: CountsTarget = _TLS.flop_counts
        except AttributeError:  # first counted op on this thread
            cnt: CountsTarget = _create_thread_state()
        if type(other) is CountedFloat:
            cnt.DIV += 1
            cnt.MUL += 1
        else:
            count_div_with_constant_divisor(other)
            if other == 1.0 or other == -1.0:
                count_mul_with_identity_multiplier(other)
            else:
                cnt.MUL += 1
        cnt.RND += 1
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

        A constant exponent 0 is the one absorbing case: IEEE 754 and C99 define pow(x, 0) as
        1.0 for every x (nan and infinities included), so the result is a compile-time constant
        of the port and comes back as a plain float — downstream folds keyed on its value then
        mirror the port's constant propagation. A CountedFloat exponent of 0.0 stays the
        runtime-POW path above.
        """
        result = float.__pow__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if not isinstance(result, float):
            return result
        if type(other) is CountedFloat:
            try:
                _TLS.flop_counts.POW += 1  # genuinely runtime exponent
            except AttributeError:  # first counted op on this thread
                _create_thread_state().POW += 1
        else:
            if float(other) == 0.0:
                return result  # the port's constant 1.0 — plain, uncounted
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

        A constant base 1 is the one absorbing case: IEEE 754 and C99 make pow(1, y) 1.0 for
        every y (nan included), so the result is a compile-time constant of the port and comes
        back as a plain float. A CountedFloat base of 1.0 stays the runtime-POW path above.
        """
        result = float.__rpow__(self, other)
        if result is NotImplemented:
            return NotImplemented
        if not isinstance(result, float):
            return result
        if type(other) is CountedFloat:
            try:
                _TLS.flop_counts.POW += 1  # genuinely runtime base
            except AttributeError:  # first counted op on this thread
                _create_thread_state().POW += 1
        else:
            if float(other) == 1.0:
                return result  # the port's constant 1.0 — plain, uncounted
            count_pow_with_constant_base(other)
        return float.__new__(CountedFloat, result)

    if hasattr(float, "from_number"):
        # Python 3.14+ only. Declared conditionally, the way the math tables register
        # version-gated functions: the member exists on CountedFloat exactly when it exists on
        # float, so surface comparisons hold in both directions on every supported interpreter.
        @classmethod
        def from_number(cls, number: object) -> CountedFloat:
            """Counted construction from a real number (float.from_number), I2F for int sources.

            CPython's from_number converts to a C double before handing the subclass constructor
            a plain float, so without this override an int source converts unpaid where
            CountedFloat(n) counts I2F -- the same source, two constructors, two answers. The
            source matrix mirrors __new__: int (bool included) counts I2F; float sources cost
            nothing; Decimal and Fraction convert uncounted, a stated gap; strings are rejected
            by the underlying call.
            """
            # resolved dynamically: on 3.13-era typeshed the member does not exist to reference
            float_from_number = getattr(float, "from_number")  # noqa: B009
            result = float_from_number(number)  # compute first: a bad source raises before counting
            if isinstance(number, int):
                try:
                    _TLS.flop_counts.I2F += 1
                except AttributeError:  # first counted op on this thread
                    _create_thread_state().I2F += 1
            return float.__new__(CountedFloat, result)
