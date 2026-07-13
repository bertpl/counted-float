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
| `math.sqrt(x)` | `SQRT` | patch | ISA | yes |
| `math.cbrt(x)` | `CBRT` | patch | benchmarked | yes |
| `math.exp(x)`, `math.exp2(x)`, `2 ** x` | `EXP`, `EXP2` | patch / operator | benchmarked | yes |
| `math.log(x[, base])` | `LOG` (or `LOG2`/`LOG10`; decomposes for other bases) | patch | benchmarked | yes |
| `math.sin`/`cos`/`tan(x)` | `SIN`, `COS`, `TAN` | patch | benchmarked | yes |
| `math.asin`/`acos`/`atan(x)` | `ASIN`, `ACOS`, `ATAN` | patch | benchmarked | yes |
| `math.atan2(y, x)` | `ATAN2` | patch | benchmarked | yes |
| `math.hypot(x, y)` | `HYPOT` | patch | benchmarked | yes |
| `math.expm1(x)`, `math.log1p(x)` | `EXPM1`, `LOG1P` | patch | benchmarked | yes |
| `math.fmod(x, y)` | `FMOD` | patch | benchmarked | yes |
| `math.sinh`/`cosh`/`tanh(x)`, `asinh`/`acosh`/`atanh(x)` | `SINH`, `COSH`, `TANH`, `ASINH`, `ACOSH`, `ATANH` | patch | benchmarked | yes |
| `math.copysign` | *(uncounted)* | — | — | no (plain float) |
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

## FlopType.ABS (`abs(x)`)

- Relevant CPU instructions
    - **ARM:** `FABS`
    - **x86:** `ANDPD`
- **Counted Python operations:** `abs(x)` and `math.fabs(x)` where `x` is a
  `CountedFloat` (both map to the same `FABS`/`ANDPD` instruction)
- **Not counted:** `numpy.abs`, `numpy.fabs`, complex abs, abs on non-CountedFloat

## FlopType.MINUS (`-x`)

- Relevant CPU instructions
    - **ARM:** `FNEG`
    - **x86:** `XORPD`
- **Counted Python operations:** Unary minus (`-x`) for `CountedFloat`
- **Not counted:** Negation on non-CountedFloat, numpy negation

## FlopType.COMP (`x<=y`, `x>y`, `x==y`, `x==0.0`, ...)

- Relevant CPU instructions
    - **ARM:** `FCMP`
    - **x86:** `(U)COMISD`
- **Counted Python operations:** `x == y`, `x != y`, `x <= y`, ... and
  `min(x,y)`, `max(x,y)` for `CountedFloat`
- **Not counted:** Comparisons on non-CountedFloat, numpy comparisons

## FlopType.RND (`round`)

- Relevant CPU instructions
    - **ARM:** `FRINT`
    - **x86:** `ROUNDSD`
- **Counted Python operations:** `round(x, n)` with explicit `n` — including
  rounding to decimals, e.g. `round(x, 2)` — for `CountedFloat` (returns
  float)
- **Not counted:** `numpy.round`, rounding on non-CountedFloat

## FlopType.F2I (`float->int`)

- Relevant CPU instructions
    - **ARM:** `FCVTZS`
    - **x86:** `CVTSD2SI`
- **Counted Python operations:** `int(x)`, `math.floor(x)`, `math.ceil(x)`,
  `math.trunc(x)`, `round(x)` for `CountedFloat` (returns int)
- **Not counted:** Conversions on non-CountedFloat, numpy conversions

## FlopType.I2F (`int->float`)

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

## FlopType.ADD (`x+y`)

- Relevant CPU instructions
    - **ARM:** `FADD`
    - **x86:** `ADDSD`
- **Counted Python operations:** `x + y` or `y + x` for `CountedFloat`
- **Not counted:** Addition on non-CountedFloat, numpy addition

## FlopType.SUB (`x-y`)

- Relevant CPU instructions
    - **ARM:** `FSUB`
    - **x86:** `SUBSD`
- **Counted Python operations:** `x - y` or `y - x` for `CountedFloat`
- **Not counted:** Subtraction on non-CountedFloat, numpy subtraction

## FlopType.MUL (`x*y`)

- Relevant CPU instructions
    - **ARM:** `FMUL`
    - **x86:** `MULSD`
- **Counted Python operations:** `x * y` or `y * x` for `CountedFloat`
- **Not counted:** Multiplication on non-CountedFloat, numpy multiplication

## FlopType.DIV (`x/y`)

- Relevant CPU instructions
    - **ARM:** `FDIV`
    - **x86:** `DIVSD`
- **Counted Python operations:** `x / y` or `y / x` for `CountedFloat`
- **Not counted:** Division on non-CountedFloat, numpy division

## FlopType.SQRT (`sqrt(x)`)

- Relevant CPU instructions
    - **ARM:** `FSQRT`
    - **x86:** `SQRTSD`
- **Counted Python operations:** `math.sqrt(x)` for `CountedFloat`
- **Not counted:** `numpy.sqrt`, sqrt on non-CountedFloat

## FlopType.CBRT (`cbrt(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cbrt(x)` for `CountedFloat`
- **Not counted:** `numpy.cbrt`, cbrt on non-CountedFloat

## FlopType.EXP (`e^x`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.exp(x)` for `CountedFloat`
- **Not counted:** `math.exp(x)` on non-CountedFloat, `numpy.exp`,
  `math.expm1`, `math.e ** x`

## FlopType.EXP2 (`2^x`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `2 ** x`, `pow(2, x)` or `math.exp2(x)` for
  `CountedFloat`
- **Not counted:** `exp2` on non-CountedFloat, `numpy.exp2`

## FlopType.EXP10 (`10^x`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `10 ** x`, `pow(10, x)` for `CountedFloat`
- **Not counted:** `10 ** x` on non-CountedFloat

## FlopType.LOG (`log(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log(x)` for `CountedFloat`;
  `math.log(x, base)` for `CountedFloat` decomposes per the constant-folding
  convention (constant base 2/10 -> LOG2/LOG10; other constant base ->
  LOG+MUL; CountedFloat base -> LOG per counted operand + DIV)
- **Not counted:** `numpy.log`, log on non-CountedFloat

## FlopType.LOG2 (`log2(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log2(x)` for `CountedFloat`;
  `math.log(x, 2)` (int base) for `CountedFloat`
- **Not counted:** `numpy.log2`, log2 on non-CountedFloat

## FlopType.LOG10 (`log10(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log10(x)` for `CountedFloat`;
  `math.log(x, 10)` (int base) for `CountedFloat`
- **Not counted:** `numpy.log10`, log10 on non-CountedFloat

## FlopType.POW (`x^y`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `x ** y`, `pow(x, y)` for `CountedFloat`; constant
  exponents/bases strength-reduce per the constant-folding convention (see the
  counting-model page): `x**0.5` -> SQRT, `x**-1` -> DIV, integer exponents
  2 <= |n| <= 16 -> their multiply chain, base 2/10 -> EXP2/EXP10
- **Not counted:** `pow` on non-CountedFloat, `numpy.pow`

## FlopType.SIN (`sin(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.sin(x)` for `CountedFloat`
- **Not counted:** `sin` on non-CountedFloat, `numpy.sin`

## FlopType.COS (`cos(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cos(x)` for `CountedFloat`
- **Not counted:** `cos` on non-CountedFloat, `numpy.cos`

## FlopType.TAN (`tan(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.tan(x)` for `CountedFloat`
- **Not counted:** `tan` on non-CountedFloat, `numpy.tan`

## FlopType.ASIN (`asin(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.asin(x)` for `CountedFloat`
- **Not counted:** `asin` on non-CountedFloat, `numpy.arcsin`

## FlopType.ACOS (`acos(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.acos(x)` for `CountedFloat`
- **Not counted:** `acos` on non-CountedFloat, `numpy.arccos`

## FlopType.ATAN (`atan(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atan(x)` for `CountedFloat`
- **Not counted:** `atan` on non-CountedFloat, `numpy.arctan`

## FlopType.ATAN2 (`atan2(y, x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atan2(y, x)` for `CountedFloat` —
  counted when *either* operand is a `CountedFloat`
- **Not counted:** `atan2` on plain floats only, `numpy.arctan2`

## FlopType.HYPOT (`hypot(x, y)`)

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

## FlopType.EXPM1 (`expm1(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.expm1(x)` for `CountedFloat`
- **Not counted:** `expm1` on non-CountedFloat, `numpy.expm1`, `math.exp(x) - 1`

## FlopType.LOG1P (`log1p(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.log1p(x)` for `CountedFloat`
- **Not counted:** `log1p` on non-CountedFloat, `numpy.log1p`, `math.log(1 + x)`

## FlopType.FMOD (`fmod(x, y)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.fmod(x, y)` for `CountedFloat` —
  counted when *either* operand is a `CountedFloat` (the C-library truncated
  remainder; distinct from the `%` operator's floored remainder)
- **Not counted:** `fmod` on plain floats only, `numpy.fmod`

## FlopType.SINH (`sinh(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.sinh(x)` for `CountedFloat`
- **Not counted:** `sinh` on non-CountedFloat, `numpy.sinh`

## FlopType.COSH (`cosh(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.cosh(x)` for `CountedFloat`
- **Not counted:** `cosh` on non-CountedFloat, `numpy.cosh`

## FlopType.TANH (`tanh(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.tanh(x)` for `CountedFloat`
- **Not counted:** `tanh` on non-CountedFloat, `numpy.tanh`

## FlopType.ASINH (`asinh(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.asinh(x)` for `CountedFloat`
- **Not counted:** `asinh` on non-CountedFloat, `numpy.arcsinh`

## FlopType.ACOSH (`acosh(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.acosh(x)` for `CountedFloat`
- **Not counted:** `acosh` on non-CountedFloat, `numpy.arccosh`

## FlopType.ATANH (`atanh(x)`)

- Relevant CPU instructions
    - **ARM:** (software)
    - **x86:** (software)
- **Counted Python operations:** `math.atanh(x)` for `CountedFloat`
- **Not counted:** `atanh` on non-CountedFloat, `numpy.arctanh`
