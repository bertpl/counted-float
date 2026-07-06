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
Two functions carry extra classification logic, applying the same
constant-detection heuristic as the `**` operator (int operand = hardcoded
constant in the source):

- `math.pow(x, y)` classifies like `x ** y`: `x**2` counts MUL, `2**x` counts
  EXP2, `10**x` counts EXP10, other cases count POW (plus I2F for an int
  operand).
- `math.log(x, base)` classifies per log variant: base omitted → LOG; int
  base 2 / 10 → LOG2 / LOG10 (a compiled port calls `log2`/`log10` directly);
  other int base → LOG + MUL (a port computes `log(x) * C` with
  `C = 1/log(base)` folded at compile time); float base → a port computes
  `log(x)/log(base)`: LOG per counted operand + DIV.

The full per-operation counting rules are in the
[FLOP types reference](flop_types.md).

Which functions are patched is also the boundary of what gets counted — see
[Known limitations](known_limitations.md).
