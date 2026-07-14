# Math patching semantics

While a `FlopCountingContext` is active, `math` module functions that require
counting (`sqrt`, `log2`, `pow`, ...) are temporarily replaced by counting
equivalents. This page documents the exact contract of that patching.

## Nothing is patched at import time

Merely importing `counted_float` leaves the process's `math` module completely
untouched. The `math` module is only patched while at least one
`FlopCountingContext` is active: patches are applied when the first context
enters and removed when the last context exits, so nested contexts behave
correctly.

## The snapshot/restore contract

The patching contract mirrors `unittest.mock.patch` / pytest `monkeypatch`
conventions:

- at first context entry, the current `math` functions are snapshotted
  (whatever they are, including other packages' patches) and the counting
  replacements delegate through them;
- at last context exit, that snapshot is restored, unconditionally — so
  `math.*` ends up exactly as it was when the first context entered.

The snapshot is (re)captured at patch time, not at import time: another
package may have applied its own `math` patches after `counted_float` was
imported, and the library delegates through — and later restores — whatever is
current, rather than silently wiping those patches.

## Composing with third-party patches

Well-nested (LIFO) third-party patching composes correctly: a patch applied
before the first context entered is delegated through while counting and still
in place after the last context exits.

Mis-nested patching is **unsupported**: a patch applied *inside* an active
counting context but not removed before the last context exits is discarded —
the library simply restores its snapshot.

## What the replacements count

The counting replacements only count operations touching `CountedFloat`
values; on plain floats they delegate straight through with no counting (see
[the counting model](counting_flops.md#the-counting-model-what-gets-counted-and-why)).
Two functions carry extra classification logic. As everywhere in the counting
model, any constant (non-`CountedFloat`) operand folds by value — it enables
strength reduction and never adds an I2F conversion:

- `math.pow(x, y)` classifies like `x ** y`: constant exponents/bases
  strength-reduce (`x**2` → MUL, `x**0.5` → SQRT, `x**-1` → DIV, small int
  exponents → their multiply chain, base 2/10 → EXP2/EXP10), other cases
  count POW.
- `math.log(x, base)` classifies per log variant: base omitted → LOG;
  constant base 2 / 10 → LOG2 / LOG10 (a compiled port calls `log2`/`log10`
  directly); other constant base → LOG + MUL (a port computes `log(x) * C`
  with `C = 1/log(base)` folded at compile time); `CountedFloat` base →
  genuinely runtime, a port computes `log(x)/log(base)`: LOG per counted
  operand + DIV.

The full per-operation counting rules are in the
[FLOP types reference](flop_types.md).

## Coverage of the `math` module

Every commonly used `math` function, and how it participates in counting:

| Coverage | Functions |
|---|---|
| **Instrumented** (patched, counts its FlopType) | `sqrt`, `cbrt`, `exp`, `exp2`, `expm1`, `log`, `log2`, `log10`, `log1p`, `pow`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`, `hypot`, `fmod`, `fabs` |
| **Counted via dunder** (no patch needed — do not expect these in the patch list) | `math.floor` / `math.ceil` / `math.trunc` → F2I through `__floor__`/`__ceil__`/`__trunc__`; the builtins `abs()` → ABS and `round()` → RND/F2I likewise count through their dunders |
| **Not instrumented** (returns a plain, uncounted `float`) | `copysign`, `remainder`, `frexp`, `ldexp`, `modf`, `degrees`, `radians`, `dist`, `fsum`, `prod`, `gamma`, `lgamma`, `erf`, `erfc`, `nextafter`, `ulp`, `fma` |

The not-instrumented set breaks contagion: the plain-`float` result silently
stops all downstream counting, so convert back with `CountedFloat(...)` if a
result of these feeds counted computation.

`math.fma(x, y, z)` (Python 3.13+) is in this set for a second reason: it is the
one place a fused multiply-add is observable at the Python level. Counting it
faithfully would need a dedicated FMA flop type; until then a multiply-add is
counted as separate MUL + ADD — see [Known limitations](known_limitations.md).

Which functions are patched is also the boundary of what gets counted — see
[Known limitations](known_limitations.md).
