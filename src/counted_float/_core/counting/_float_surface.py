"""Classification of the float attribute surface that CountedFloat inherits unchanged.

The math-surface tables pin every public `math` callable to a classification, so a function a
future CPython adds fails a test instead of becoming a silently uncounted hole.  This module is
the same pin for `float`'s own attribute surface: every member of `dir(float)` that CountedFloat
does not override is listed here with the reason it needs no override, and the float-surface test
holds `dir(float)` to the union of these tables and the class's own overrides -- in both
directions, so a member that appears, disappears, or changes provenance fails loudly.

Two tables, split by where the member is defined.  The provenance matters because the two halves
drift for different reasons: the float-defined half moves with `float` itself, while the
object-defined half moves with `object` (as `__getstate__` did when 3.11 added it) -- churn there
is legible as plumbing, not as a counting question.  The test asserts each member's provenance,
so a member migrating between halves (e.g. `float` growing its own `__str__`, which would change
what `str(x)` prints) is a failure rather than a silent behavior change.

Members are registered conditionally where CPython does the same, so both directions of the
surface comparison hold on every supported interpreter without version checks in the test.
"""

# Float-defined inherited members: each computes on (or presents) the float's value, and each
# needs no override for a stated reason.  The reasons are the load-bearing part -- they are what
# a future maintainer cites when a new member looks similar to an existing one.
_FLOAT_DEFINED_UNPATCHED: dict[str, str] = {
    "imag": (
        "plain +0.0 for every receiver, signs and nan payloads included: a compile-time constant "
        "of the port, per the cost model's constant-result convention (the receiver-dependent "
        "real / conjugate preserve countedness instead)"
    ),
    "hex": (
        "produces a str that leaves the algorithm; the hex digits are the mantissa's own nibbles, "
        "so the port emits no floating-point instruction -- the remaining work is integer/bit "
        "manipulation, which this library counts nowhere"
    ),
    "fromhex": (
        "preserves countedness: CPython wraps the parsed double through the subclass constructor, "
        "so the result is a CountedFloat; the strtod-shaped parse itself has no FlopType -- a "
        "stated gap (CountedFloat(3) costs I2F where fromhex('0x1.8p+1') costs nothing)"
    ),
    "__float__": (
        "the documented escape hatch: an explicit, uncounted exit from the counting model -- "
        "double->double identity, no instruction in the port. Safe because it is explicit at the "
        "call site, which is exactly what the implicit property access real lacks"
    ),
    "__bool__": (
        "truthiness is deliberately uncounted bookkeeping: the interpreter inserts it implicitly "
        "at every if/while/and/or/not/assert with no opt-out, and python -O elides assert "
        "entirely, so a count here would vary with interpreter flags; the algorithmic spelling "
        "x != 0.0 counts COMP"
    ),
    "__format__": (
        "formatting produces a str that leaves the algorithm; correctly-rounded decimal "
        "conversion is the machinery round(x, n) declares unmodeled -- except the '%' "
        "presentation type, which scales by 100 in binary64 first: one MUL, a labeled uncounted "
        "exception (unobservable from Python, and the result cannot re-enter the algorithm)"
    ),
    "__getnewargs__": (
        "pickling (protocol 2+) and copy/deepcopy: hands __new__ a plain-float 1-tuple, so "
        "round-trips rebuild a CountedFloat at zero count -- deserialization is not the "
        "algorithm converting an integer"
    ),
}
if hasattr(float, "__getformat__"):
    # CPython's own docstring disclaims this introspection helper; registered conditionally so
    # its eventual removal fails nothing.
    _FLOAT_DEFINED_UNPATCHED["__getformat__"] = (
        "structurally not a float operation: binds to the type and reads no value (its return "
        "string is endianness-dependent, so only existence is pinned)"
    )

# Object-defined inherited members: plumbing that computes no float value.  Pinned so that churn
# in `object`'s surface -- or a member migrating to float-defined -- is a test failure with a
# name attached rather than a silent hole.
_OBJECT_PLUMBING = "object plumbing: computes no float value"
# Members whose defining class moved between supported interpreters, so the provenance pin
# tolerates either side for them. `float.__getattribute__` has its own entry in float.__dict__ on
# 3.11 and falls through to object's from 3.12 on; the behavior is identical either way, and
# pinning one arrangement would encode a single interpreter's layout as the contract.
_PROVENANCE_VARIES_BY_VERSION = frozenset({"__getattribute__"})
_OBJECT_DEFINED_UNPATCHED: dict[str, str] = {
    "__class__": _OBJECT_PLUMBING,
    "__dir__": _OBJECT_PLUMBING,
    "__getattribute__": _OBJECT_PLUMBING,
    "__init__": (
        "object.__init__ no-op: the narrowed __new__ is the sole arity gate, so "
        "CountedFloat(1.0, 2.0) fails in __new__ before this ever runs"
    ),
    "__setattr__": "refuses attribute mutation (empty __slots__), matching plain float",
    "__delattr__": "refuses attribute mutation (empty __slots__), matching plain float",
    "__sizeof__": (
        "reports memory, computes no float value (the byte count is build-dependent -- 3.14t "
        "differs -- so only existence is pinned)"
    ),
    "__subclasshook__": _OBJECT_PLUMBING,
    "__str__": (
        "presentation: float defines no __str__ of its own, so str(x) falls through "
        "object.__str__ to the loud CountedFloat.__repr__ -- the single presentation mechanism; "
        "provenance is pinned because a future float-defined __str__ would silently change what "
        "str(x) prints"
    ),
    "__getstate__": (
        "pickling: returns None because __slots__ is empty -- no instance state exists to "
        "serialize; pinned because it guards the __slots__ decision"
    ),
    "__reduce__": (
        "pickling: delegates through copyreg and rebuilds a CountedFloat at zero count; "
        "reachable only by direct call (pickle routes through __reduce_ex__)"
    ),
    "__reduce_ex__": (
        "pickling (protocols 0-1): routes through copyreg and float(), rebuilding a CountedFloat "
        "at zero count with no CountedFloat override participating -- pinned because that route "
        "is pure CPython machinery"
    ),
}
