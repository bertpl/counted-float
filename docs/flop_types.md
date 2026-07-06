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

## FlopType.ABS (`abs(x)`)

- Relevant CPU instructions
    - **ARM:** `FABS`
    - **x86:** `ANDPD`
- **Counted Python operations:** `abs(x)` where `x` is a `CountedFloat`
- **Not counted:** `numpy.abs`, complex abs, abs on non-CountedFloat

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
- **Counted Python operations:** `round(x, 0)` for `CountedFloat` (returns
  float)
- **Not counted:** `numpy.round`, rounding with decimals, rounding on
  non-CountedFloat

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
- **Counted Python operations:** Construction of `CountedFloat` from int, any
  binary operation where one operand is an int and the other a `CountedFloat`
  (e.g., `x + 3`, `3 * x`, etc.)
- **Not counted:** `float(n)`, unitary operations (e.g. `math.sqrt` on
  integers -> convert to `CountedFloat` first)

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
  `math.log(x, base)` for `CountedFloat` decomposes per the constant-detection
  heuristic (int base 2/10 -> LOG2/LOG10; other int base -> LOG+MUL; float
  base -> LOG per counted operand + DIV)
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
- **Counted Python operations:** `x ** y`, `pow(x, y)` for `CountedFloat`
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
