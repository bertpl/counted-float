# The float surface

`CountedFloat` inherits from `float`, so every attribute `float` exposes is part of the
counting model's surface — not just the arithmetic operators. This page is the account of
that surface, the sibling of the
[`math` coverage table](math_patching.md#coverage-of-the-math-module): every member of
`dir(float)` participates in exactly one way — **counted** through an override, **reported**
at WARNING verbosity, or **deliberately uncounted** with the reason stated below — and a test
holds the surface to that partition on every supported interpreter, so an attribute a future
CPython adds fails a test instead of becoming a silently uncounted hole.

## Counted members

The arithmetic and comparison operators are covered per operation in the
[FLOP types reference](flop_types.md). Beyond those, these members count or preserve
countedness:

| Member | Counts | Result |
|---|---|---|
| `x.real`, `x.conjugate()` | *(nothing — they return the receiver's own bits, like `+x`)* | `CountedFloat`, bit-identical |
| `x.is_integer()` | `RND + COMP` — CPython computes `floor(x) == x` in doubles, the price of the counted spelling `x // 1.0 == x` (RND, not F2I: no int materializes) | `bool` |
| `CountedFloat(n)`, int source | `I2F` — the port's int→double conversion instruction | `CountedFloat` |
| `CountedFloat.from_number(n)` (Python 3.14+), int source | `I2F` — the same answer as the constructor, for the same source | `CountedFloat` |

The complex-protocol trio gets two answers on purpose: `real` and `conjugate()` are
receiver-*dependent* (they hand back the receiver's own bits, so dropping the type would
silently stop downstream counting), while `imag` is receiver-*independent* — `+0.0` for every
possible receiver, signs and nan payloads included — which makes it a compile-time constant
of the port; see its row below.

## Reported at WARNING verbosity

`x.as_integer_ratio()` is uncounted — the port's extraction is a bit-field read plus an
integer shift, work outside the floating-point domain the model prices — but its result is
the one on this surface that can silently re-enter float arithmetic: `n, d =
x.as_integer_ratio(); n / d` resumes uncounted at zero flops. It is therefore reported
through the same once-per-call-site WARNING channel as the uncounted `math` helpers — see
[watching what gets counted](counting_flops.md#watching-what-gets-counted).

`float(x)` is *not* reported, deliberately: it is the documented exit from the counting
model, and what makes it safe is that leaving the counted world is the explicit point of the
call — unlike a representation query whose parts happen to re-enter.

## Deliberately uncounted members

Everything `CountedFloat` inherits unchanged, with the reason it needs no override:

<!-- BEGIN generated: float-surface-table -->
| Member | Why it needs no override |
|---|---|
| `__bool__` | truthiness is deliberately uncounted bookkeeping: the interpreter inserts it implicitly at every if/while/and/or/not/assert with no opt-out, and python -O elides assert entirely, so a count here would vary with interpreter flags; the algorithmic spelling x != 0.0 counts COMP |
| `__float__` | the documented escape hatch: an explicit, uncounted exit from the counting model -- double->double identity, no instruction in the port. Safe because it is explicit at the call site, which is exactly what the implicit property access real lacks |
| `__format__` | formatting produces a str that leaves the algorithm; correctly-rounded decimal conversion is the machinery round(x, n) declares unmodeled -- except the '%' presentation type, which scales by 100 in binary64 first: one MUL, a labeled uncounted exception (unobservable from Python, and the result cannot re-enter the algorithm) |
| `__getformat__` | structurally not a float operation: binds to the type and reads no value (its return string is endianness-dependent, so only existence is pinned) |
| `__getnewargs__` | pickling (protocol 2+) and copy/deepcopy: hands __new__ a plain-float 1-tuple, so round-trips rebuild a CountedFloat at zero count -- deserialization is not the algorithm converting an integer |
| `fromhex` | preserves countedness: CPython wraps the parsed double through the subclass constructor, so the result is a CountedFloat; the strtod-shaped parse itself has no FlopType -- a stated gap (CountedFloat(3) costs I2F where fromhex('0x1.8p+1') costs nothing) |
| `hex` | produces a str that leaves the algorithm; the hex digits are the mantissa's own nibbles, so the port emits no floating-point instruction -- the remaining work is integer/bit manipulation, which this library counts nowhere |
| `imag` | plain +0.0 for every receiver, signs and nan payloads included: a compile-time constant of the port, per the cost model's constant-result convention (the receiver-dependent real / conjugate preserve countedness instead) |
| `__class__` *(object plumbing)* | object plumbing: computes no float value |
| `__delattr__` *(object plumbing)* | refuses attribute mutation (empty __slots__), matching plain float |
| `__dir__` *(object plumbing)* | object plumbing: computes no float value |
| `__getattribute__` *(object plumbing)* | object plumbing: computes no float value |
| `__getstate__` *(object plumbing)* | pickling: returns None because __slots__ is empty -- no instance state exists to serialize; pinned because it guards the __slots__ decision |
| `__init__` *(object plumbing)* | object.__init__ no-op: the narrowed __new__ is the sole arity gate, so CountedFloat(1.0, 2.0) fails in __new__ before this ever runs |
| `__reduce__` *(object plumbing)* | pickling: delegates through copyreg and rebuilds a CountedFloat at zero count; reachable only by direct call (pickle routes through __reduce_ex__) |
| `__reduce_ex__` *(object plumbing)* | pickling (protocols 0-1): routes through copyreg and float(), rebuilding a CountedFloat at zero count with no CountedFloat override participating -- pinned because that route is pure CPython machinery |
| `__setattr__` *(object plumbing)* | refuses attribute mutation (empty __slots__), matching plain float |
| `__sizeof__` *(object plumbing)* | reports memory, computes no float value (the byte count is build-dependent -- 3.14t differs -- so only existence is pinned) |
| `__str__` *(object plumbing)* | presentation: float defines no __str__ of its own, so str(x) falls through object.__str__ to the loud CountedFloat.__repr__ -- the single presentation mechanism; provenance is pinned because a future float-defined __str__ would silently change what str(x) prints |
| `__subclasshook__` *(object plumbing)* | object plumbing: computes no float value |
<!-- END generated: float-surface-table -->

## The presentation contract

`__repr__` is the single presentation mechanism, and it is deliberately loud:
`repr(x)`, `str(x)`, `print(x)`, `f"{x}"` and `format(x, "")` all render
`CountedFloat(1.5)` — `float` defines no `__str__` of its own, so every empty-spec spelling
falls through to the repr. Whether a value silently fell out of the counting system is this
library's central hazard, and the repr is the zero-cost place it shows.

Any **non-empty** format spec formats the plain value instead — `f"{x:.2f}"` gives `1.50`,
and even a bare alignment (`f"{x:>10}"`) flips to plain rendering — so reports and tables
keep their layout. The loud/quiet boundary is exactly `spec == ""`.

One formatting subtlety is a labeled exception rather than a derivation: the `%`
presentation type multiplies by 100 in binary64 before converting (`f"{x:.1%}"`), and that
one MUL is uncounted — it is unobservable from Python, and the resulting `str` cannot
re-enter the algorithm.

## Pickling and copying

Pickling, `copy.copy` and `copy.deepcopy` round-trip a `CountedFloat` to a `CountedFloat` at
zero count, on both mechanisms pickle uses: protocols 2+ rebuild through `__getnewargs__`
and the class's own constructor, protocols 0–1 through `copyreg` and plain CPython
machinery. The zero count is correct — deserialization is not the algorithm converting an
integer — and bit-exactness holds from protocol 1 up (protocol 0 stores floats as repr text,
which loses nan payloads; plain-float behavior, not a `CountedFloat` difference).
