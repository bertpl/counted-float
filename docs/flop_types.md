# FLOP types

This page provides detailed information about how each floating-point
operation (FLOP) type is counted and analyzed in the `counted-float` package.
All `math.*` entries below assume an active `FlopCountingContext` (outside
one, the `math` module is not instrumented — see
[Math patching semantics](math_patching.md)). For each flop type, you will
find:

- Relevant scalar instructions for ARM (v8+) and x86 (SSE2+)
- Python operations that are counted for this flop type
- Python operations that are *not* counted for this flop type

The rules deciding *how* each type is priced (compiled-port lens, real-call lens, and the
documented fallback) are stated in [Cost-model principles](cost_model.md).

## Coverage at a glance

| Python operation | Counts as | Mechanism | Weight source | Stays `CountedFloat`? |
|---|---|---|---|---|
| `x + y`, `x - y`, `x * y` | `ADD`, `SUB`, `MUL` (sign-exact identity constants fold: `* 1.0` / `- 0.0` / `+ (-0.0)` → nothing, `* -1.0` / `(-0.0) - x` → `MINUS`) | operator | ISA | yes |
| `x / y` | `DIV` (`MUL` for a power-of-two constant divisor — the exact reciprocal fold; `MINUS` for `x / -1.0`; nothing for `x / 1.0`) | operator | ISA | yes |
| `x // y` | `DIV + RND` (the division step folds like `/` for constant divisors) | operator (decomposed) | ISA | yes |
| `x % y` | `DIV + RND + MUL + SUB` (the division step folds like `/` for constant divisors; a `±1.0` divisor folds the multiply step too — away for `1.0`, to `MINUS` for `-1.0`) | operator (decomposed) | ISA | yes |
| `divmod(x, y)` | `DIV + RND + MUL + SUB` (folds like `%`, division step and multiply step alike) | operator (decomposed) | ISA | yes (both) |
| `-x` | `MINUS` | operator | ISA | yes |
| `+x` | *(nothing)* | operator | — | yes |
| `abs(x)`, `math.fabs(x)` | `ABS` | operator / patch | ISA | yes |
| `x == y`, `x < y`, … | `COMP` | operator | ISA | returns `bool` |
| `min(x, y, ...)`, `max(x, y, ...)` | `COMP` per comparison | operator | ISA | returns the winning operand — plain when a plain constant wins; re-wrap with `CountedFloat(...)` to keep counting |
| `round(x, 0)` | `RND` | operator | ISA | yes (float) |
| `round(x, n)`, `n != 0` | `MUL + RND + DIV` | operator (decomposed) | ISA | yes (float) |
| `round(x)`, `int(x)`, `math.floor`/`ceil`/`trunc` | `F2I` | operator | ISA | returns `int` |
| `CountedFloat(int)` | `I2F` | constructor | ISA | yes |
| `x ** y`, `math.pow(x, y)` | `POW` (or cheaper via constant strength reduction — MULs, SQRT, DIV, EXP2, EXP10) | operator / patch | benchmarked | yes |
| `math.fma(x, y, z)` (3.13+) | `FMA` (or `ADD` when both multiplicands are constant; nothing when their product is exactly `-0.0`) | patch | ISA | yes |
| `math.sqrt(x)` | `SQRT` | patch | ISA | yes |
| `math.cbrt(x)` | `CBRT` | patch | benchmarked | yes |
| `math.exp(x)`, `math.exp2(x)`, `2 ** x` | `EXP`, `EXP2` | patch / operator | benchmarked | yes |
| `math.log(x[, base])` | `LOG` (or `LOG2`/`LOG10`; decomposes for other bases) | patch | benchmarked | yes |
| `math.sin`/`cos`/`tan(x)` | `SIN`, `COS`, `TAN` | patch | benchmarked | yes |
| `math.asin`/`acos`/`atan(x)` | `ASIN`, `ACOS`, `ATAN` | patch | benchmarked | yes |
| `math.atan2(y, x)` | `ATAN2` | patch | benchmarked | yes |
| `math.hypot(x, y, ...)` | `HYPOT` + (n−2) `HYPOT_XARG` (1 arg → `ABS`) | patch | benchmarked | yes |
| `math.expm1(x)`, `math.log1p(x)` | `EXPM1`, `LOG1P` | patch | benchmarked | yes |
| `math.fmod(x, y)` | `FMOD` | patch | benchmarked | yes |
| `math.remainder(x, y)` | `REMAINDER` | patch | benchmarked | yes |
| `math.sinh`/`cosh`/`tanh(x)`, `asinh`/`acosh`/`atanh(x)` | `SINH`, `COSH`, `TANH`, `ASINH`, `ACOSH`, `ATANH` | patch | benchmarked | yes |
| `math.gamma`/`lgamma(x)` | `GAMMA`, `LGAMMA` | patch | benchmarked | yes |
| `math.erf`/`erfc(x)` | `ERF`, `ERFC` | patch | benchmarked | yes |
| `math.copysign(x, y)` | `COPYSIGN` | patch | benchmarked | yes |
| `math.fmax(x, y)`, `math.fmin(x, y)` (3.15+) | `COMP` (the NaN-quieting guard is unpriced) | patch | ISA | yes — unlike the builtins, whichever operand wins |
| `math.degrees(x)`, `math.radians(x)` | `MUL` *(decomposed)* | patch | — | yes |
| `math.dist(p, q)` | `DIST` + (n−2) `DIST_XARG` (1-D → `SUB + ABS`) | patch | benchmarked | yes |
| `math.prod(xs)` | one `MUL` per chained multiply *(decomposed)* | patch | — | yes |
| `math.fsum(xs)` | (n−1) `ADD` *(decomposed; compensation machinery not modeled)* | patch | — | yes |
| `math.sumprod(p, q)` (3.12+) | `SUMPROD` + (n−2) `SUMPROD_XELEM` | patch | benchmarked | yes |
| `numpy.*` and other non-stdlib math | *(uncounted)* | — | — | no |

- **Mechanism** — *operator*: a `CountedFloat` dunder, counted everywhere.
  *patch*: a `math.*` function, counted only inside a `FlopCountingContext`
  (see [Math patching semantics](math_patching.md)). *decomposed*: no
  dedicated `FlopType` — counts as a composition of existing types.
- **Weight source** — *ISA*: backed by a real hardware instruction (spec-sheet
  latency + benchmarks). *benchmarked*: a libm-level op with no corresponding
  instruction, so its weight comes from benchmarks alone.

### Decomposed operations

`//`, `%`, and `divmod()` have no dedicated `FlopType`: a compiled port emits
each as a sequence of primitive operations, and that sequence is what gets
counted. Python's `//`/`%` use **floored** semantics, so `⌊·⌋` below is a
float→float round (`RND`), not an `F2I`:

- `x // y` → `DIV + RND` — divide, then floor the quotient.
- `x % y` → `DIV + RND + MUL + SUB` — the floored remainder `r = x − y·⌊x/y⌋`.
- `divmod(x, y)` → `DIV + RND + MUL + SUB` — quotient and remainder share the
  `DIV + RND`, so it costs the same as a lone `%`.

For a constant divisor the division step folds like a bare `/`, and a `±1.0` divisor also
folds the `y·⌊x/y⌋` multiply — the divisor is that multiply's constant factor, so the
identity folds apply to it: away for `1.0`, `MINUS` for `-1.0`.

`round(x, n)` with a nonzero digit count decomposes the same way:

- `round(x, n)`, `n != 0` → `MUL + RND + DIV` — scale into the digit position,
  round, scale back. The unscale is a true divide (the scale factor is a power
  of ten, whose reciprocal is not exact). Stated gap: CPython itself computes
  this via correctly-rounded decimal conversion, whose input-dependent cost the
  port price knowingly omits. `round(x, 0)` needs no scaling and counts a lone
  `RND`.

Note the `%` operator (floored) is distinct from `math.fmod` (the truncated C
remainder, which has its own `FlopType.FMOD`). `math.log(x, base)` also
decomposes for bases other than 2/10 — see `FlopType.LOG` below.

## FlopType.ABS (`abs(x)`) { #flop-abs }

- Relevant CPU instructions
    - **ARM:** `FABS`
    - **x86:** `ANDPD`
- **Counted Python operations:** `abs(x)` and `math.fabs(x)` where `x` is a
  `CountedFloat` (both map to the same `FABS`/`ANDPD` instruction); one ABS
  inside `math.isinf` / `math.isfinite` (the classifier's `fabs`-then-compare),
  one inside `math.isnormal` / `math.issubnormal` (the magnitude their range
  test takes once) and three inside `math.isclose`'s core
- **Not counted:** `numpy.abs`, `numpy.fabs`, complex abs, abs on non-CountedFloat
- **Weight measurement:** [the machine code behind the `ABS` weight](machine_code/abs.md)

## FlopType.MINUS (`-x`) { #flop-minus }

- Relevant CPU instructions
    - **ARM:** `FNEG`
    - **x86:** `XORPD`
- **Counted Python operations:** Unary minus (`-x`) for `CountedFloat`
- **Not counted:** Negation on non-CountedFloat, numpy negation
- **Weight measurement:** [the machine code behind the `MINUS` weight](machine_code/minus.md)

## FlopType.COPYSIGN (`copysign(x,y)`) { #flop-copysign }

- Relevant CPU instructions
    - **ARM:** `BIT` (bitwise insert with a sign mask — a single instruction)
    - **x86:** `ANDPD` + `ANDPD` + `ORPD` (no dedicated instruction: clear the sign of `x`,
      isolate the sign of `y`, merge)
- **Counted Python operations:** `math.copysign(x, y)` where `x` or `y` is a `CountedFloat`
  (and only there — `math.signbit`, which reads the same bit, counts COMP instead: see
  [the decomposed operations](cost_model.md#decomposed-operations))
- **Not counted:** copysign on non-CountedFloat, numpy copysign
- **Note:** same sign-bit instruction class as ABS and MINUS, but 1–3 ops depending on
  architecture — which is why it is measured as its own benchmarked flop type rather than
  assumed equal to ABS. Its weight comes from benchmarks only (like the libm functions);
  vendor latency tables have no row for it.
- **Weight measurement:** [the machine code behind the `COPYSIGN` weight](machine_code/copysign.md)

## FlopType.COMP (`x<=y`, `x>y`, `x==y`, `x==0.0`, ...) { #flop-comp }

- Relevant CPU instructions
    - **ARM:** `FCMP`
    - **x86:** `(U)COMISD`
- **Counted Python operations:** `x == y`, `x != y`, `x <= y`, ... and
  `min(x,y)`, `max(x,y)` for `CountedFloat`; the selections `math.fmax(x,y)` /
  `math.fmin(x,y)` (the compare-and-select a port emits); the float classifiers —
  `math.isnan` (the self-compare a port emits), one COMP inside `math.isinf` /
  `math.isfinite`, two inside `math.isnormal` / `math.issubnormal` (their two
  range bounds), one for `math.signbit` (the sole charge: its question has no FP
  form to decompose), three inside `math.isclose`'s core, and `is_integer()`'s
  compare
- **Not counted:** Comparisons on non-CountedFloat, numpy comparisons, and
  truthiness (`bool(x)`, `if x:`, `assert x`) — a deliberate, labeled exception.
  The interpreter inserts the test implicitly at every `if` / `while` / `and` /
  `or` / `not` / `assert` with no opt-out, and `python -O` elides `assert`
  entirely, so a truthiness count would price interpreter bookkeeping and vary
  with interpreter flags — no port-faithful count does either. Write an
  algorithmic zero-test as `x != 0.0` to have it counted
- **Note:** the *builtin* `min`/`max` return the winning operand *object*, not a
  `bool` — with mixed counted/plain arguments the winner may be the plain
  constant, which ends countedness; see
  [known limitations](known_limitations.md#other-limitations). `math.fmax` /
  `math.fmin` are not affected: they build a fresh result, which the patch wraps,
  so countedness survives whichever operand wins
- **Weight measurement:** [the machine code behind the `COMP` weight](machine_code/comp.md)

## FlopType.RND (`round`) { #flop-rnd }

- Relevant CPU instructions
    - **ARM:** `FRINT`
    - **x86:** `ROUNDSD`
- **Counted Python operations:** `round(x, 0)` for `CountedFloat` (returns
  float), plus the round step inside the decomposed operations — `round(x, n)`
  with nonzero `n` (`MUL + RND + DIV`) and the floor of `x // y` / `x % y` /
  `divmod`
- **Not counted:** `numpy.round`, rounding on non-CountedFloat
- **Weight measurement:** [the machine code behind the `RND` weight](machine_code/rnd.md)

## FlopType.F2I (`float->int`) { #flop-f2i }

- Relevant CPU instructions
    - **ARM:** `FCVTZS`
    - **x86:** `CVTSD2SI`
- **Counted Python operations:** `int(x)`, `math.floor(x)`, `math.ceil(x)`,
  `math.trunc(x)`, `round(x)` for `CountedFloat` (returns int)
- **Not counted:** Conversions on non-CountedFloat, numpy conversions

## FlopType.I2F (`int->float`) { #flop-i2f }

- Relevant CPU instructions
    - **ARM:** `SCVTF`
    - **x86:** `CVTSI2SD`
- **Counted Python operations:** Construction of `CountedFloat` from an int,
  e.g. `CountedFloat(3)` — the way to opt a genuine runtime integer into the
  counting model
- **Not counted:** `float(n)`; an `int` operand in arithmetic, comparisons, or
  `**` (e.g. `x + 3`, `3 * x`, `x < 2`, `x**3`) — an `int` operand is a
  compile-time constant, folded to a float literal by a compiled port, so it
  adds no conversion (see [Counting FLOPs](counting_flops.md))

## FlopType.ADD (`x+y`) { #flop-add }

- Relevant CPU instructions
    - **ARM:** `FADD`
    - **x86:** `ADDSD`
- **Counted Python operations:** `x + y` or `y + x` for `CountedFloat`
- **Not counted:** Addition on non-CountedFloat, numpy addition
- **Weight measurement:** [the machine code behind the `ADD` weight](machine_code/add.md)

## FlopType.SUB (`x-y`) { #flop-sub }

- Relevant CPU instructions
    - **ARM:** `FSUB`
    - **x86:** `SUBSD`
- **Counted Python operations:** `x - y` or `y - x` for `CountedFloat`
- **Not counted:** Subtraction on non-CountedFloat, numpy subtraction
- **Weight measurement:** [the machine code behind the `SUB` weight](machine_code/sub.md)

## FlopType.MUL (`x*y`) { #flop-mul }

- Relevant CPU instructions
    - **ARM:** `FMUL`
    - **x86:** `MULSD`
- **Counted Python operations:** `x * y` or `y * x` for `CountedFloat`
- **Not counted:** Multiplication on non-CountedFloat, numpy multiplication
- **Weight measurement:** [the machine code behind the `MUL` weight](machine_code/mul.md)

## FlopType.DIV (`x/y`) { #flop-div }

- Relevant CPU instructions
    - **ARM:** `FDIV`
    - **x86:** `DIVSD`
- **Counted Python operations:** `x / y` or `y / x` for `CountedFloat` —
  except division by a power-of-two constant divisor of either sign with a finite reciprocal,
  which counts `MUL`: for exactly those divisors `x * (1/c)` is bit-identical
  to `x / c`, so a compiled port applies the reciprocal fold. `x / 1.0` counts
  nothing at all (it folds away entirely, mirroring `x ** 1`)
- **Not counted:** Division on non-CountedFloat, numpy division
- **Weight measurement:** [the machine code behind the `DIV` weight](machine_code/div.md)

## FlopType.FMA (`x*y+z`) { #flop-fma }

- Relevant CPU instructions
    - **ARM:** `FMADD`
    - **x86:** `VFMADD213SD`
- **Counted Python operations:** `math.fma(x, y, z)` (Python 3.13+) — counted
  when *any* operand is a `CountedFloat`, as one fused multiply-add: a single
  instruction with a single rounding
- **Constant multiplicands decompose:** when *both* `x` and `y` are constants
  their product folds at compile time, leaving a compiled port with a bare add,
  so that counts ADD rather than FMA — and a collapsed product of exactly
  `-0.0` folds the add away too (`z + (-0.0)` is `z` for every `z`), counting
  nothing. A surviving `fma` gets no reduction by constant *value*: the
  explicit call stays fused by the author-boundary pin — written fused stays
  fused, even where a bit-exact cheaper respelling exists (see
  [the counting model](counting_flops.md#the-counting-model-what-gets-counted-and-why))
- **Not counted:** `math.fma` on plain floats only; `a*b + c` written with
  operators, which counts MUL + ADD because the interpreter cannot observe the
  fusion (see [Known limitations](known_limitations.md))
- **Weight measurement:** [the machine code behind the `FMA` weight](machine_code/fma.md)

## FlopType.SQRT (`sqrt(x)`) { #flop-sqrt }

- Relevant CPU instructions
    - **ARM:** `FSQRT`
    - **x86:** `SQRTSD`
- **Counted Python operations:** `math.sqrt(x)` for `CountedFloat`
- **Not counted:** `numpy.sqrt`, sqrt on non-CountedFloat
- **Weight measurement:** [the machine code behind the `SQRT` weight](machine_code/sqrt.md)

## FlopType.CBRT (`cbrt(x)`) { #flop-cbrt }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cbrt(x)` for `CountedFloat`
- **Not counted:** `numpy.cbrt`, cbrt on non-CountedFloat
- **Weight measurement:** [the machine code behind the `CBRT` weight](machine_code/cbrt.md)

## FlopType.EXP (`e^x`) { #flop-exp }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.exp(x)` for `CountedFloat`
- **Not counted:** `math.exp(x)` on non-CountedFloat, `numpy.exp`,
  `math.expm1`, `math.e ** x`
- **Note:** `math.e ** x` counts POW, not EXP — `math.e` is not e (no float is;
  e is irrational), so `pow(math.e, x)` and `exp(x)` compute different
  functions, and neither the bit-exact compiler stage nor the same-computation
  author stage of the [cost model](cost_model.md) admits the rewrite. Contrast
  `math.log(x, math.e)`, whose fold rides a `1/log(base)` multiplier that
  evaluates to exactly 1.0 (see [`FlopType.LOG`](#flop-log))
- **Weight measurement:** [the machine code behind the `EXP` weight](machine_code/exp.md)

## FlopType.EXP2 (`2^x`) { #flop-exp2 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `2 ** x`, `pow(2, x)` or `math.exp2(x)` for
  `CountedFloat`
- **Not counted:** `exp2` on non-CountedFloat, `numpy.exp2`
- **Weight measurement:** [the machine code behind the `EXP2` weight](machine_code/exp2.md)

## FlopType.EXP10 (`10^x`) { #flop-exp10 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `10 ** x`, `pow(10, x)` for `CountedFloat`
- **Not counted:** `10 ** x` on non-CountedFloat
- **Weight measurement:** [the machine code behind the `EXP10` weight](machine_code/exp10.md)

## FlopType.LOG (`log(x)`) { #flop-log }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log(x)` for `CountedFloat`;
  `math.log(x, base)` for `CountedFloat` decomposes per the constant-folding
  convention (constant base 2/10 -> LOG2/LOG10; other constant base ->
  LOG+MUL, where the multiply itself identity-folds when `1/log(base)` is
  exactly ±1.0 — e.g. base `math.e`; CountedFloat base -> LOG per counted
  operand + DIV)
- **Not counted:** `numpy.log`, log on non-CountedFloat
- **Weight measurement:** [the machine code behind the `LOG` weight](machine_code/log.md)

## FlopType.LOG2 (`log2(x)`) { #flop-log2 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log2(x)` for `CountedFloat`;
  `math.log(x, 2)` (int base) for `CountedFloat`
- **Not counted:** `numpy.log2`, log2 on non-CountedFloat
- **Weight measurement:** [the machine code behind the `LOG2` weight](machine_code/log2.md)

## FlopType.LOG10 (`log10(x)`) { #flop-log10 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log10(x)` for `CountedFloat`;
  `math.log(x, 10)` (int base) for `CountedFloat`
- **Not counted:** `numpy.log10`, log10 on non-CountedFloat
- **Weight measurement:** [the machine code behind the `LOG10` weight](machine_code/log10.md)

## FlopType.POW (`x^y`) { #flop-pow }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `x ** y`, `pow(x, y)` for `CountedFloat`; constant
  exponents/bases strength-reduce per the constant-folding convention (see the
  counting-model page): `x**0.5` -> SQRT, `x**-1` -> DIV, integer exponents
  2 <= |n| <= 16 -> their multiply chain, base 2/10 -> EXP2/EXP10
- **Not counted:** `pow` on non-CountedFloat, `numpy.pow`; a negative base
  under a fractional exponent with either operand counted, whose result is a
  plain `complex` — it leaves the real-float domain the model prices, so
  nothing is counted and contagion ends
- **Weight measurement:** [the machine code behind the `POW` weight](machine_code/pow.md)

## FlopType.SIN (`sin(x)`) { #flop-sin }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.sin(x)` for `CountedFloat`
- **Not counted:** `sin` on non-CountedFloat, `numpy.sin`
- **Weight measurement:** [the machine code behind the `SIN` weight](machine_code/sin.md)

## FlopType.COS (`cos(x)`) { #flop-cos }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cos(x)` for `CountedFloat`
- **Not counted:** `cos` on non-CountedFloat, `numpy.cos`
- **Weight measurement:** [the machine code behind the `COS` weight](machine_code/cos.md)

## FlopType.TAN (`tan(x)`) { #flop-tan }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.tan(x)` for `CountedFloat`
- **Not counted:** `tan` on non-CountedFloat, `numpy.tan`
- **Weight measurement:** [the machine code behind the `TAN` weight](machine_code/tan.md)

## FlopType.ASIN (`asin(x)`) { #flop-asin }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.asin(x)` for `CountedFloat`
- **Not counted:** `asin` on non-CountedFloat, `numpy.arcsin`
- **Weight measurement:** [the machine code behind the `ASIN` weight](machine_code/asin.md)

## FlopType.ACOS (`acos(x)`) { #flop-acos }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.acos(x)` for `CountedFloat`
- **Not counted:** `acos` on non-CountedFloat, `numpy.arccos`
- **Weight measurement:** [the machine code behind the `ACOS` weight](machine_code/acos.md)

## FlopType.ATAN (`atan(x)`) { #flop-atan }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atan(x)` for `CountedFloat`
- **Not counted:** `atan` on non-CountedFloat, `numpy.arctan`
- **Weight measurement:** [the machine code behind the `ATAN` weight](machine_code/atan.md)

## FlopType.ATAN2 (`atan2(y, x)`) { #flop-atan2 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atan2(y, x)` for `CountedFloat` —
  counted when *either* operand is a `CountedFloat`
- **Not counted:** `atan2` on plain floats only, `numpy.arctan2`
- **Weight measurement:** [the machine code behind the `ATAN2` weight](machine_code/atan2.md)

## FlopType.HYPOT (`hypot(x, y, ...)`) { #flop-hypot }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.hypot(...)` for `CountedFloat` — counted
  once per call when *any* coordinate is a `CountedFloat`; coordinates beyond
  the second each add a [`HYPOT_XARG`](#flop-hypot-xarg), and a 1-argument call
  counts `ABS` instead (it computes `|x|`)
- **Not counted:** `hypot` on plain floats only, `numpy.hypot`
- **Weight measurement:** [the machine code behind the `HYPOT` weight](machine_code/hypot.md)

## FlopType.HYPOT_XARG (`hypot(x, y, z, ...)`) { #flop-hypot-xarg }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** one per coordinate beyond the second of a
  `math.hypot` call: an n-ary call counts `HYPOT` + (n−2) `HYPOT_XARG`
- **Not counted:** 2-argument calls (they cost the base `HYPOT` alone)
- **Note:** the per-extra-coordinate slope of the overflow-safe scaled
  algorithm `math.hypot` executes — far cheaper than a whole extra call, since
  the extra coordinate's squares overlap the shared scaling and `sqrt`
- **Weight measurement:** [the machine code behind the `HYPOT_XARG` weight](machine_code/hypot_xarg.md)

## FlopType.DIST (`dist(p, q)`) { #flop-dist }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.dist(p, q)` for `CountedFloat` — counted
  once per call when *any* coordinate is a `CountedFloat`; coordinates beyond
  the second each add a [`DIST_XARG`](#flop-dist-xarg), and a 1-D call counts
  `SUB + ABS` instead: the coordinate difference through the same
  single-coordinate shortcut as 1-argument `hypot`
- **Not counted:** `dist` on plain floats only, numpy norms/distances
- **Note:** the 2-D base price of the overflow-safe algorithm `math.dist`
  executes; it sits above `HYPOT` by the per-coordinate subtraction work its
  offset carries
- **Weight measurement:** [the machine code behind the `DIST` weight](machine_code/dist.md)

## FlopType.DIST_XARG (`dist(p, q)`, 3+ dimensions) { #flop-dist-xarg }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** one per dimension beyond the second of a
  `math.dist` call: an n-dimensional call counts `DIST` + (n−2) `DIST_XARG`
- **Not counted:** 2-dimensional calls (they cost the base `DIST` alone) and
  1-dimensional calls (`SUB + ABS`)
- **Weight measurement:** [the machine code behind the `DIST_XARG` weight](machine_code/dist_xarg.md)

## FlopType.SUMPROD (`sumprod(p,q)`) { #flop-sumprod }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.sumprod(p, q)` (Python 3.12+) for
  `CountedFloat` — counted once per call when *any* element is a
  `CountedFloat`; elements beyond the second each add a
  [`SUMPROD_XELEM`](#flop-sumprod-xelem)
- **Not counted:** `sumprod` on plain floats only, `numpy.dot` and friends
- **Note:** the 2-element base price (close-out included) of the
  extended-precision (TripleLength) accumulation `math.sumprod` executes;
  counted inputs are unboxed to plain floats before delegating, so the
  exact-float production algorithm runs — a `CountedFloat` element would
  otherwise silently reroute the call to a naive object path
- **Weight measurement:** [the machine code behind the `SUMPROD` weight](machine_code/sumprod.md)

## FlopType.SUMPROD_XELEM (`sumprod(p,q)`, 3+ elements) { #flop-sumprod-xelem }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** one per element beyond the second of a
  `math.sumprod` call: an n-element call counts `SUMPROD` + (n−2)
  `SUMPROD_XELEM`
- **Not counted:** 1- and 2-element calls (they cost the base `SUMPROD` alone)
- **Note:** far below the per-element cost a decomposed compensation chain
  would suggest — the algorithm's lanes overlap, and the measured slope
  captures that overlap
- **Weight measurement:** [the machine code behind the `SUMPROD_XELEM` weight](machine_code/sumprod_xelem.md)

## FlopType.EXPM1 (`expm1(x)`) { #flop-expm1 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.expm1(x)` for `CountedFloat`
- **Not counted:** `expm1` on non-CountedFloat, `numpy.expm1`, `math.exp(x) - 1`
- **Weight measurement:** [the machine code behind the `EXPM1` weight](machine_code/expm1.md)

## FlopType.LOG1P (`log1p(x)`) { #flop-log1p }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log1p(x)` for `CountedFloat`
- **Not counted:** `log1p` on non-CountedFloat, `numpy.log1p`, `math.log(1 + x)`
- **Weight measurement:** [the machine code behind the `LOG1P` weight](machine_code/log1p.md)

## FlopType.FMOD (`fmod(x, y)`) { #flop-fmod }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.fmod(x, y)` for `CountedFloat` —
  counted when *either* operand is a `CountedFloat` (the C-library truncated
  remainder; distinct from the `%` operator's floored remainder)
- **Not counted:** `fmod` on plain floats only, `numpy.fmod`
- **Weight measurement:** [the machine code behind the `FMOD` weight](machine_code/fmod.md)

## FlopType.REMAINDER (`remainder(x, y)`) { #flop-remainder }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.remainder(x, y)` for `CountedFloat` —
  counted when *either* operand is a `CountedFloat` (the IEEE 754
  round-to-nearest remainder; distinct from both `math.fmod` and the `%`
  operator)
- **Not counted:** `remainder` on plain floats only, `numpy.remainder` (which
  computes the floored `%` semantics, not this function)
- **Weight measurement:** [the machine code behind the `REMAINDER` weight](machine_code/remainder.md)

## FlopType.SINH (`sinh(x)`) { #flop-sinh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.sinh(x)` for `CountedFloat`
- **Not counted:** `sinh` on non-CountedFloat, `numpy.sinh`
- **Weight measurement:** [the machine code behind the `SINH` weight](machine_code/sinh.md)

## FlopType.COSH (`cosh(x)`) { #flop-cosh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cosh(x)` for `CountedFloat`
- **Not counted:** `cosh` on non-CountedFloat, `numpy.cosh`
- **Weight measurement:** [the machine code behind the `COSH` weight](machine_code/cosh.md)

## FlopType.TANH (`tanh(x)`) { #flop-tanh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.tanh(x)` for `CountedFloat`
- **Not counted:** `tanh` on non-CountedFloat, `numpy.tanh`
- **Weight measurement:** [the machine code behind the `TANH` weight](machine_code/tanh.md)

## FlopType.ASINH (`asinh(x)`) { #flop-asinh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.asinh(x)` for `CountedFloat`
- **Not counted:** `asinh` on non-CountedFloat, `numpy.arcsinh`
- **Weight measurement:** [the machine code behind the `ASINH` weight](machine_code/asinh.md)

## FlopType.ACOSH (`acosh(x)`) { #flop-acosh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.acosh(x)` for `CountedFloat`
- **Not counted:** `acosh` on non-CountedFloat, `numpy.arccosh`
- **Weight measurement:** [the machine code behind the `ACOSH` weight](machine_code/acosh.md)

## FlopType.ATANH (`atanh(x)`) { #flop-atanh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atanh(x)` for `CountedFloat`
- **Not counted:** `atanh` on non-CountedFloat, `numpy.arctanh`
- **Weight measurement:** [the machine code behind the `ATANH` weight](machine_code/atanh.md)

## FlopType.GAMMA (`gamma(x)`) { #flop-gamma }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.gamma(x)` for `CountedFloat`
- **Not counted:** gamma on non-CountedFloat, `scipy.special.gamma`
- **Weight measurement:** [the machine code behind the `GAMMA` weight](machine_code/gamma.md)

## FlopType.LGAMMA (`lgamma(x)`) { #flop-lgamma }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.lgamma(x)` for `CountedFloat`
- **Not counted:** lgamma on non-CountedFloat, `scipy.special.gammaln`, `math.log(math.gamma(x))` (which counts GAMMA + LOG)
- **Weight measurement:** [the machine code behind the `LGAMMA` weight](machine_code/lgamma.md)

## FlopType.ERF (`erf(x)`) { #flop-erf }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.erf(x)` for `CountedFloat`
- **Not counted:** erf on non-CountedFloat, `scipy.special.erf`
- **Weight measurement:** [the machine code behind the `ERF` weight](machine_code/erf.md)

## FlopType.ERFC (`erfc(x)`) { #flop-erfc }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.erfc(x)` for `CountedFloat`
- **Not counted:** erfc on non-CountedFloat, `scipy.special.erfc`, `1 - math.erf(x)` (which counts ERF + SUB)
- **Weight measurement:** [the machine code behind the `ERFC` weight](machine_code/erfc.md)
