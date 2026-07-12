# Counting FLOPs

## The `CountedFloat` class

In order to instrument all floating point operations with counting
functionality, the `CountedFloat` class was implemented, which is a drop-in
replacement for the built-in `float` type. The `CountedFloat` class is a
subclass of `float` and is "contagious", meaning that it will automatically
ensure results of math operations where at least one operand is a
`CountedFloat` will also be a `CountedFloat`. This way we ensure flop counting
is a 'closed system'.

On top of this, `math` module functions that require counting (`sqrt`, `log2`,
`pow`, ...) are also instrumented: while a `FlopCountingContext` is active
(see below), they are temporarily replaced by counting equivalents. Outside
such a context — including at plain `import` time — the `math` module is left
completely untouched (see [Math patching semantics](math_patching.md) for the
exact contract).

**Example**:

```python
from counted_float import CountedFloat

cf = CountedFloat(1.3)
f = 2.8

result = cf + f  # result = CountedFloat(4.1)

is_float_1 = isinstance(cf, float)  # True
is_float_2 = isinstance(result, float)  # True
```

## The counting model: what gets counted and why

The counting model is a contract with two sides:

- **Your side:** wrap every *runtime input* of the algorithm you want to
  measure in `CountedFloat` at its boundary. Contagion does the rest —
  everything derived from those inputs stays counted automatically.
- **The library's side:** count every FLOP that a compiled (C/Rust/...) port
  of your algorithm would execute *on data derived from those inputs*.

From this contract follows a clean rule for everything else: **constants are
free.** Any plain float encountered mid-computation is, by the contract, not
an input — so it must be a constant of the algorithm (a literal, a
coefficient, a tolerance), and operations purely among constants are work a
compiled port would fold at compile time or precompute. This is why e.g.
`math.sqrt(3)` counts nothing: the port ships `sqrt(3)` as a precomputed
constant.

The library detects constants through two mechanisms, applying the same rule:

- **Unwrapped values** (plain floats): constants by the wrapping contract, as
  above.
- **`int` operands**: evidence of a *hardcoded* constant — ints don't fall out
  of floating-point computations, so an int operand almost certainly appears
  literally in your source. As a constant it is folded to a float literal by a
  compiled port, so an `int` operand adds **no `I2F` conversion**; it merely
  enables the strength reductions such a port would apply: `x**2` counts MUL
  (i.e. `x*x`), `2**x` counts EXP2, `math.log(x, 10)` counts LOG10 — while
  `x**2.0`, with a float that *could* be a runtime value, conservatively counts
  a generic POW.

The one place an `I2F` conversion *is* counted is explicit construction from an
int — `CountedFloat(n)`. That is exactly how you opt a genuine runtime integer
(a loop index, a computed count) into the counting model: wrap it, and its
int→float conversion counts like any other FLOP.

The flip side: an unwrapped runtime input is invisible to the counter — that
is a wrapping error at your algorithm's boundary, not something the library
can detect. When in doubt, wrap.

One more consequence of the context-scoped `math` patching: `math.*` calls
participate in counting (and in contagion) only while a `FlopCountingContext`
is active. Operator-based contagion (`+`, `*`, `**`, ...) works everywhere,
but counts are meant to be read through a context — so the practical rule is
simply: run your measured algorithm inside one.

Not everything is counted — see [Known limitations](known_limitations.md) for
what falls outside the counting model (e.g. `numpy` operations).

## FLOP counting context managers

Once we use the `CountedFloat` class, we can use the available context
managers to count the number of flops performed by `CountedFloat` objects.

**Example 1**: _basic usage_

```python
from counted_float import CountedFloat, FlopCountingContext

cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 * cf2
    _ = cf1 + cf2

counts = ctx.flop_counts()   # {FlopType.MUL: 1, FlopType.ADD: 1}
counts.total_count()         # 2
```

**Example 2**: _math module functions_

```python
import math
from counted_float import CountedFloat, FlopCountingContext

cf1 = CountedFloat(0.81)

with FlopCountingContext() as ctx:
    s = math.sqrt(cf1)  # s = CountedFloat(0.9)

counts = ctx.flop_counts()   # {FlopType.SQRT: 1}
```

Note that `math.*` functions are only instrumented *inside* the context:
outside it, `math.sqrt(cf1)` returns a plain `float` and counts nothing.

**Example 3**: _pause counting 1_

```python
from counted_float import CountedFloat, FlopCountingContext

cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 * cf2
    ctx.pause()
    _ = cf1 + cf2   # will be executed but not counted
    ctx.resume()
    _ = cf1 - cf2

counts = ctx.flop_counts()   # {FlopType.MUL: 1, FlopType.SUB: 1}
counts.total_count()         # 2
```

**Example 4**: _pause counting 2_

```python
from counted_float import CountedFloat, FlopCountingContext, PauseFlopCounting

cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 * cf2
    with PauseFlopCounting():
        _ = cf1 + cf2   # will be executed but not counted
    _ = cf1 - cf2

counts = ctx.flop_counts()   # {FlopType.MUL: 1, FlopType.SUB: 1}
counts.total_count()         # 2
```
