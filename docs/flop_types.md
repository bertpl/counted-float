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

## Coverage at a glance

| Python operation | Counts as | Mechanism | Weight source | Stays `CountedFloat`? |
|---|---|---|---|---|
| `x + y`, `x - y`, `x * y`, `x / y` | `ADD`, `SUB`, `MUL`, `DIV` | operator | ISA | yes |
| `x // y` | `DIV + RND` | operator (decomposed) | ISA | yes |
| `x % y` | `DIV + RND + MUL + SUB` | operator (decomposed) | ISA | yes |
| `divmod(x, y)` | `DIV + RND + MUL + SUB` | operator (decomposed) | ISA | yes (both) |
| `-x` | `MINUS` | operator | ISA | yes |
| `+x` | *(nothing)* | operator | — | yes |
| `abs(x)`, `math.fabs(x)` | `ABS` | operator / patch | ISA | yes |
| `x == y`, `x < y`, …, `min`, `max` | `COMP` | operator | ISA | returns `bool` |
| `round(x, n)` | `RND` | operator | ISA | yes (float) |
| `round(x)`, `int(x)`, `math.floor`/`ceil`/`trunc` | `F2I` | operator | ISA | returns `int` |
| `CountedFloat(int)` | `I2F` | constructor | ISA | yes |
| `x ** y`, `math.pow(x, y)` | `POW` (or cheaper via constant strength reduction — MULs, SQRT, DIV, EXP2, EXP10) | operator / patch | benchmarked | yes |
| `math.fma(x, y, z)` (3.13+) | `FMA` (or `ADD` when both multiplicands are constant) | patch | ISA | yes |
| `math.sqrt(x)` | `SQRT` | patch | ISA | yes |
| `math.cbrt(x)` | `CBRT` | patch | benchmarked | yes |
| `math.exp(x)`, `math.exp2(x)`, `2 ** x` | `EXP`, `EXP2` | patch / operator | benchmarked | yes |
| `math.log(x[, base])` | `LOG` (or `LOG2`/`LOG10`; decomposes for other bases) | patch | benchmarked | yes |
| `math.sin`/`cos`/`tan(x)` | `SIN`, `COS`, `TAN` | patch | benchmarked | yes |
| `math.asin`/`acos`/`atan(x)` | `ASIN`, `ACOS`, `ATAN` | patch | benchmarked | yes |
| `math.atan2(y, x)` | `ATAN2` | patch | benchmarked | yes |
| `math.hypot(x, y)` | `HYPOT` (2 args; 3+ decompose to n MUL + (n−1) ADD + SQRT, 1 to ABS) | patch | benchmarked | yes |
| `math.expm1(x)`, `math.log1p(x)` | `EXPM1`, `LOG1P` | patch | benchmarked | yes |
| `math.fmod(x, y)` | `FMOD` | patch | benchmarked | yes |
| `math.sinh`/`cosh`/`tanh(x)`, `asinh`/`acosh`/`atanh(x)` | `SINH`, `COSH`, `TANH`, `ASINH`, `ACOSH`, `ATANH` | patch | benchmarked | yes |
| `math.copysign(x, y)` | `COPYSIGN` | patch | benchmarked | yes |
| `math.degrees(x)`, `math.radians(x)` | `MUL` *(decomposed)* | patch | — | yes |
| `math.dist(p, q)` | n `SUB` + n `MUL` + (n−1) `ADD` + `SQRT` *(decomposed)* | patch | — | yes |
| `math.prod(xs)` | one `MUL` per chained multiply *(decomposed)* | patch | — | yes |
| `math.fsum(xs)` | (n−1) `ADD` *(decomposed; compensation machinery not modeled)* | patch | — | yes |
| `math.sumprod(p, q)` (3.12+) | *(uncounted)* | — | — | no |
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

Note the `%` operator (floored) is distinct from `math.fmod` (the truncated C
remainder, which has its own `FlopType.FMOD`). `math.log(x, base)` also
decomposes for bases other than 2/10 — see `FlopType.LOG` below.

## FlopType.ABS (`abs(x)`) { #flop-abs }

- Relevant CPU instructions
    - **ARM:** `FABS`
    - **x86:** `ANDPD`
- **Counted Python operations:** `abs(x)` and `math.fabs(x)` where `x` is a
  `CountedFloat` (both map to the same `FABS`/`ANDPD` instruction)
- **Not counted:** `numpy.abs`, `numpy.fabs`, complex abs, abs on non-CountedFloat
- **Weight measurement:** [the machine code behind the `ABS` weight](kernel_asm/abs.md)

## FlopType.MINUS (`-x`) { #flop-minus }

- Relevant CPU instructions
    - **ARM:** `FNEG`
    - **x86:** `XORPD`
- **Counted Python operations:** Unary minus (`-x`) for `CountedFloat`
- **Not counted:** Negation on non-CountedFloat, numpy negation
- **Weight measurement:** [the machine code behind the `MINUS` weight](kernel_asm/minus.md)

## FlopType.COPYSIGN (`copysign(x,y)`) { #flop-copysign }

- Relevant CPU instructions
    - **ARM:** `BIT` (bitwise insert with a sign mask — a single instruction)
    - **x86:** `ANDPD` + `ANDPD` + `ORPD` (no dedicated instruction: clear the sign of `x`,
      isolate the sign of `y`, merge)
- **Counted Python operations:** `math.copysign(x, y)` where `x` or `y` is a `CountedFloat`
- **Not counted:** copysign on non-CountedFloat, numpy copysign
- **Note:** same sign-bit instruction class as ABS and MINUS, but 1–3 ops depending on
  architecture — which is why it is measured as its own benchmarked flop type rather than
  assumed equal to ABS. Its weight comes from benchmarks only (like the libm functions);
  vendor latency tables have no row for it.
- **Weight measurement:** [the machine code behind the `COPYSIGN` weight](kernel_asm/copysign.md)

## FlopType.COMP (`x<=y`, `x>y`, `x==y`, `x==0.0`, ...) { #flop-comp }

- Relevant CPU instructions
    - **ARM:** `FCMP`
    - **x86:** `(U)COMISD`
- **Counted Python operations:** `x == y`, `x != y`, `x <= y`, ... and
  `min(x,y)`, `max(x,y)` for `CountedFloat`
- **Not counted:** Comparisons on non-CountedFloat, numpy comparisons
- **Weight measurement:** [the machine code behind the `COMP` weight](kernel_asm/comp.md)

## FlopType.RND (`round`) { #flop-rnd }

- Relevant CPU instructions
    - **ARM:** `FRINT`
    - **x86:** `ROUNDSD`
- **Counted Python operations:** `round(x, n)` with explicit `n` — including
  rounding to decimals, e.g. `round(x, 2)` — for `CountedFloat` (returns
  float)
- **Not counted:** `numpy.round`, rounding on non-CountedFloat
- **Weight measurement:** [the machine code behind the `RND` weight](kernel_asm/rnd.md)

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
- **Weight measurement:** [the machine code behind the `ADD` weight](kernel_asm/add.md)

## FlopType.SUB (`x-y`) { #flop-sub }

- Relevant CPU instructions
    - **ARM:** `FSUB`
    - **x86:** `SUBSD`
- **Counted Python operations:** `x - y` or `y - x` for `CountedFloat`
- **Not counted:** Subtraction on non-CountedFloat, numpy subtraction
- **Weight measurement:** [the machine code behind the `SUB` weight](kernel_asm/sub.md)

## FlopType.MUL (`x*y`) { #flop-mul }

- Relevant CPU instructions
    - **ARM:** `FMUL`
    - **x86:** `MULSD`
- **Counted Python operations:** `x * y` or `y * x` for `CountedFloat`
- **Not counted:** Multiplication on non-CountedFloat, numpy multiplication
- **Weight measurement:** [the machine code behind the `MUL` weight](kernel_asm/mul.md)

## FlopType.DIV (`x/y`) { #flop-div }

- Relevant CPU instructions
    - **ARM:** `FDIV`
    - **x86:** `DIVSD`
- **Counted Python operations:** `x / y` or `y / x` for `CountedFloat`
- **Not counted:** Division on non-CountedFloat, numpy division
- **Weight measurement:** [the machine code behind the `DIV` weight](kernel_asm/div.md)

## FlopType.FMA (`x*y+z`) { #flop-fma }

- Relevant CPU instructions
    - **ARM:** `FMADD`
    - **x86:** `VFMADD213SD`
- **Counted Python operations:** `math.fma(x, y, z)` (Python 3.13+) — counted
  when *any* operand is a `CountedFloat`, as one fused multiply-add: a single
  instruction with a single rounding
- **Constant multiplicands decompose:** when *both* `x` and `y` are constants
  their product folds at compile time, leaving a compiled port with a bare add,
  so that counts ADD rather than FMA. No reduction is done by constant *value* —
  every FMA variant is one instruction, so there is nothing to win (see
  [the counting model](counting_flops.md#the-counting-model-what-gets-counted-and-why))
- **Not counted:** `math.fma` on plain floats only; `a*b + c` written with
  operators, which counts MUL + ADD because the interpreter cannot observe the
  fusion (see [Known limitations](known_limitations.md))
- **Weight measurement:** [the machine code behind the `FMA` weight](kernel_asm/fma.md)

## FlopType.SQRT (`sqrt(x)`) { #flop-sqrt }

- Relevant CPU instructions
    - **ARM:** `FSQRT`
    - **x86:** `SQRTSD`
- **Counted Python operations:** `math.sqrt(x)` for `CountedFloat`
- **Not counted:** `numpy.sqrt`, sqrt on non-CountedFloat
- **Weight measurement:** [the machine code behind the `SQRT` weight](kernel_asm/sqrt.md)

## FlopType.CBRT (`cbrt(x)`) { #flop-cbrt }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cbrt(x)` for `CountedFloat`
- **Not counted:** `numpy.cbrt`, cbrt on non-CountedFloat
- **Weight measurement:** [the machine code behind the `CBRT` weight](kernel_asm/cbrt.md)

## FlopType.EXP (`e^x`) { #flop-exp }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.exp(x)` for `CountedFloat`
- **Not counted:** `math.exp(x)` on non-CountedFloat, `numpy.exp`,
  `math.expm1`, `math.e ** x`
- **Weight measurement:** [the machine code behind the `EXP` weight](kernel_asm/exp.md)

## FlopType.EXP2 (`2^x`) { #flop-exp2 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `2 ** x`, `pow(2, x)` or `math.exp2(x)` for
  `CountedFloat`
- **Not counted:** `exp2` on non-CountedFloat, `numpy.exp2`
- **Weight measurement:** [the machine code behind the `EXP2` weight](kernel_asm/exp2.md)

## FlopType.EXP10 (`10^x`) { #flop-exp10 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `10 ** x`, `pow(10, x)` for `CountedFloat`
- **Not counted:** `10 ** x` on non-CountedFloat
- **Weight measurement:** [the machine code behind the `EXP10` weight](kernel_asm/exp10.md)

## FlopType.LOG (`log(x)`) { #flop-log }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log(x)` for `CountedFloat`;
  `math.log(x, base)` for `CountedFloat` decomposes per the constant-folding
  convention (constant base 2/10 -> LOG2/LOG10; other constant base ->
  LOG+MUL; CountedFloat base -> LOG per counted operand + DIV)
- **Not counted:** `numpy.log`, log on non-CountedFloat
- **Weight measurement:** [the machine code behind the `LOG` weight](kernel_asm/log.md)

## FlopType.LOG2 (`log2(x)`) { #flop-log2 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log2(x)` for `CountedFloat`;
  `math.log(x, 2)` (int base) for `CountedFloat`
- **Not counted:** `numpy.log2`, log2 on non-CountedFloat
- **Weight measurement:** [the machine code behind the `LOG2` weight](kernel_asm/log2.md)

## FlopType.LOG10 (`log10(x)`) { #flop-log10 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log10(x)` for `CountedFloat`;
  `math.log(x, 10)` (int base) for `CountedFloat`
- **Not counted:** `numpy.log10`, log10 on non-CountedFloat
- **Weight measurement:** [the machine code behind the `LOG10` weight](kernel_asm/log10.md)

## FlopType.POW (`x^y`) { #flop-pow }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `x ** y`, `pow(x, y)` for `CountedFloat`; constant
  exponents/bases strength-reduce per the constant-folding convention (see the
  counting-model page): `x**0.5` -> SQRT, `x**-1` -> DIV, integer exponents
  2 <= |n| <= 16 -> their multiply chain, base 2/10 -> EXP2/EXP10
- **Not counted:** `pow` on non-CountedFloat, `numpy.pow`
- **Weight measurement:** [the machine code behind the `POW` weight](kernel_asm/pow.md)

## FlopType.SIN (`sin(x)`) { #flop-sin }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.sin(x)` for `CountedFloat`
- **Not counted:** `sin` on non-CountedFloat, `numpy.sin`
- **Weight measurement:** [the machine code behind the `SIN` weight](kernel_asm/sin.md)

## FlopType.COS (`cos(x)`) { #flop-cos }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cos(x)` for `CountedFloat`
- **Not counted:** `cos` on non-CountedFloat, `numpy.cos`
- **Weight measurement:** [the machine code behind the `COS` weight](kernel_asm/cos.md)

## FlopType.TAN (`tan(x)`) { #flop-tan }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.tan(x)` for `CountedFloat`
- **Not counted:** `tan` on non-CountedFloat, `numpy.tan`
- **Weight measurement:** [the machine code behind the `TAN` weight](kernel_asm/tan.md)

## FlopType.ASIN (`asin(x)`) { #flop-asin }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.asin(x)` for `CountedFloat`
- **Not counted:** `asin` on non-CountedFloat, `numpy.arcsin`
- **Weight measurement:** [the machine code behind the `ASIN` weight](kernel_asm/asin.md)

## FlopType.ACOS (`acos(x)`) { #flop-acos }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.acos(x)` for `CountedFloat`
- **Not counted:** `acos` on non-CountedFloat, `numpy.arccos`
- **Weight measurement:** [the machine code behind the `ACOS` weight](kernel_asm/acos.md)

## FlopType.ATAN (`atan(x)`) { #flop-atan }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atan(x)` for `CountedFloat`
- **Not counted:** `atan` on non-CountedFloat, `numpy.arctan`
- **Weight measurement:** [the machine code behind the `ATAN` weight](kernel_asm/atan.md)

## FlopType.ATAN2 (`atan2(y, x)`) { #flop-atan2 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atan2(y, x)` for `CountedFloat` —
  counted when *either* operand is a `CountedFloat`
- **Not counted:** `atan2` on plain floats only, `numpy.arctan2`
- **Weight measurement:** [the machine code behind the `ATAN2` weight](kernel_asm/atan2.md)

## FlopType.HYPOT (`hypot(x, y)`) { #flop-hypot }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.hypot(x, y, ...)` for `CountedFloat` —
  counted once when *any* coordinate is a `CountedFloat`
- **Not counted:** `hypot` on plain floats only, `numpy.hypot`
- **Arity assumption:** `HYPOT` is modeled as a 2D primitive. `math.hypot`
  accepts any number of coordinates, but an n-D call still counts a single
  `HYPOT` — under-counting vs. the n·MUL + (n−1)·ADD + SQRT a port would
  execute. Decompose manually if n-D `hypot` cost matters.
- **Weight measurement:** [the machine code behind the `HYPOT` weight](kernel_asm/hypot.md)

## FlopType.EXPM1 (`expm1(x)`) { #flop-expm1 }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.expm1(x)` for `CountedFloat`
- **Not counted:** `expm1` on non-CountedFloat, `numpy.expm1`, `math.exp(x) - 1`
- **Weight measurement:** [the machine code behind the `EXPM1` weight](kernel_asm/expm1.md)

## FlopType.LOG1P (`log1p(x)`) { #flop-log1p }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log1p(x)` for `CountedFloat`
- **Not counted:** `log1p` on non-CountedFloat, `numpy.log1p`, `math.log(1 + x)`
- **Weight measurement:** [the machine code behind the `LOG1P` weight](kernel_asm/log1p.md)

## FlopType.FMOD (`fmod(x, y)`) { #flop-fmod }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.fmod(x, y)` for `CountedFloat` —
  counted when *either* operand is a `CountedFloat` (the C-library truncated
  remainder; distinct from the `%` operator's floored remainder)
- **Not counted:** `fmod` on plain floats only, `numpy.fmod`
- **Weight measurement:** [the machine code behind the `FMOD` weight](kernel_asm/fmod.md)

## FlopType.SINH (`sinh(x)`) { #flop-sinh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.sinh(x)` for `CountedFloat`
- **Not counted:** `sinh` on non-CountedFloat, `numpy.sinh`
- **Weight measurement:** [the machine code behind the `SINH` weight](kernel_asm/sinh.md)

## FlopType.COSH (`cosh(x)`) { #flop-cosh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cosh(x)` for `CountedFloat`
- **Not counted:** `cosh` on non-CountedFloat, `numpy.cosh`
- **Weight measurement:** [the machine code behind the `COSH` weight](kernel_asm/cosh.md)

## FlopType.TANH (`tanh(x)`) { #flop-tanh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.tanh(x)` for `CountedFloat`
- **Not counted:** `tanh` on non-CountedFloat, `numpy.tanh`
- **Weight measurement:** [the machine code behind the `TANH` weight](kernel_asm/tanh.md)

## FlopType.ASINH (`asinh(x)`) { #flop-asinh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.asinh(x)` for `CountedFloat`
- **Not counted:** `asinh` on non-CountedFloat, `numpy.arcsinh`
- **Weight measurement:** [the machine code behind the `ASINH` weight](kernel_asm/asinh.md)

## FlopType.ACOSH (`acosh(x)`) { #flop-acosh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.acosh(x)` for `CountedFloat`
- **Not counted:** `acosh` on non-CountedFloat, `numpy.arccosh`
- **Weight measurement:** [the machine code behind the `ACOSH` weight](kernel_asm/acosh.md)

## FlopType.ATANH (`atanh(x)`) { #flop-atanh }

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atanh(x)` for `CountedFloat`
- **Not counted:** `atanh` on non-CountedFloat, `numpy.arctanh`
- **Weight measurement:** [the machine code behind the `ATANH` weight](kernel_asm/atanh.md)
