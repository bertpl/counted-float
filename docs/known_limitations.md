# Known limitations

## numpy counting is an explicit non-goal

The counting model prices scalar code as a compiled port would execute it;
array operations are bulk vectorized routines outside that model, and no part of numpy's
semantics is adopted. Concretely:

- `np.float64` scalars work and count correctly on **either** side of an
  operator — not because numpy is supported, but because `np.float64` is a
  plain C double subclassing `float`, so it flows through the ordinary float
  path.
- mixing `CountedFloat` with numpy **arrays**, or with numpy scalar dtypes
  that do not subclass `float` (`np.float32`, `np.int64`, ...), raises
  `TypeError`. `CountedFloat` refuses numpy's ufunc protocol
  (`__array_ufunc__ = None`) on purpose: the alternative is an operation that
  silently returns an *uncounted* result whose type may later recover to
  `CountedFloat`, hiding that flops went missing — the loud boundary is the
  honest one.

Keep counted algorithms in scalar `float`/`CountedFloat` code; hand values to
numpy only after converting to plain `float` (e.g. `float(x)`), outside the
counted region.

## Constant folding keys on the operand's value, not on it being a literal

The [cost model](cost_model.md) presents a plain `float` operand as a
compile-time [constant](glossary.md#constant) — something the imaginary
compiled program knows while being compiled. The implementation cannot see the
source, so it applies that rule to the operand's **runtime value**: any plain
`float` is treated as a constant, whether it was written as a literal or
arrived from somewhere else.

The two readings coincide for a value that really is fixed. They come apart when
one call site meets *different* plain floats over its lifetime:

```python
x = CountedFloat(10.0)
for divisor in (2.0, 3.0, 4.0, 5.0):
    _ = x / divisor           # MUL, DIV, MUL, DIV
```

That single division counts **2 MUL + 2 DIV**: the powers of two fold to exact
reciprocal multiplication, the others do not. No compiled port produces that
mix — a real program has one instruction there, chosen once at compile time. The
model's central premise is what quietly breaks, not merely a weight.

The discipline that avoids it: **anything that varies while the algorithm runs
should be a `CountedFloat`**, so it is priced as dynamic input rather than
folded on whatever value it happens to hold. Reserve plain floats for values
that are genuinely fixed.

This is named rather than fixed: detecting it would mean inspecting the caller's
syntax tree to see whether the operand was a literal, which is out of
proportion to a modelling assumption that correct usage already avoids. It is
observable, though — a counting context asked to
[report what it counts](counting_flops.md#watching-what-gets-counted) logs each
fold with the reason it was applied, so a site being folded inconsistently shows
up in that output.

## Loops the library cannot count as loops

`math.prod` and `math.fsum` count n−1 operations for n elements, whatever the
elements hold. The built-in `sum`, `min` and `max`, and any loop written by
hand, cannot be counted that way: the library cannot patch them, so their counts
come from the individual operator calls, and each of those applies the ordinary
constant folds.

Counting through the operator calls goes wrong in two directions:

- **one addition too many** in `sum(data)` over counted values: `sum` seeds with
  an integer `0`, and adding zero is not a no-op for signed zero
  (`-0.0 + 0.0` is `+0.0`), so `+ 0` is counted exactly as a strict compiler
  would emit it. An explicit `0.0` seed changes nothing, for the same reason.
- **too few operations** whenever plain floats precede the first `CountedFloat`:
  those operations have no counted operand at all, so `sum([1.0, 2.0, cf])`
  counts one addition where a loop runs two, and `min([1.0, 2.0, cf, 3.0])` one
  comparison where a loop runs three.

Two fixes, with different reach:

- **`math.fsum(data)` or `math.prod(data)`** — n−1 operations for n elements,
  every element counted whatever its value. There is no equivalent for
  `min`/`max`.
- **seed a counted accumulator** — `sum(data[1:], start=CountedFloat(data[0]))`,
  and the same shape for a loop written by hand. Every later operation then has
  a counted operand, so it counts. Elements that fold against that accumulator
  are still dropped, by the identity folds of
  [the cost model](cost_model.md#the-rules) as everywhere else — a `-0.0` added
  or a `1.0` multiplied costs nothing.

## Other limitations

- the uncounted built-in operations are cataloged per surface: the `math`
  module's not-instrumented set (`frexp`, `ldexp`, `modf`, `nextafter`,
  `ulp` — the port emits no floating-point instruction for them; see the
  [`math` coverage table](math_patching.md#coverage-of-the-math-module)) and
  `float`'s own uncounted members (`hex()`, `as_integer_ratio()`, formatting,
  truthiness — see [the float surface](float_surface.md)). A counting context
  can be asked to report the contagion-relevant ones as it meets them, so a
  count that is quietly missing them says so — see
  [watching what gets counted](counting_flops.md#watching-what-gets-counted)
- operator-level fused multiply-add is not modeled: `a*b + c` counts as separate
  MUL + ADD, matching the contraction-off reference semantics the
  [cost model](cost_model.md) pins. Real builds routinely contract: on aarch64,
  FP contraction is the compiler *default* at plain `-O2` (no fast-math flag
  involved), and x86 FMA3 targets fuse under the same defaults — so on such
  builds, flop counts over-estimate fusable multiply-add sequences (dot
  products, Horner evaluation) by up to the fused sequences' MUL share.
  Python cannot observe operator-level fusion, so the library cannot count it.
  `math.fma` (Python 3.13+) is the one place a fusion *is* observable, and it is
  counted as a single `FMA`; expressing a multiply-add that way is therefore the
  only means of having one counted as fused — and there is none on older
  interpreters, where `math.fma` does not exist
- mixed operations with non-float numeric types are outside the counting
  model: `CountedFloat` delegates to the other operand exactly like `float`
  does, so e.g. `CountedFloat(x) * Fraction(1, 2)` yields a correct but plain —
  and uncounted — `float` result (downstream counting stops). The reverse order
  counts normally: `Fraction` hands the operation back, and the `CountedFloat`
  performs it. A `decimal.Decimal` operand raises `TypeError` just as with plain
  `float`, in either order. *Comparisons* with a `Fraction` register 1 ABS +
  2 COMP even though the comparison is delegated: `Fraction`'s own float
  handling guards with `math.isnan` and `math.isinf`, and the classifiers count
  for a counted operand whoever calls them — the same honest-count stance as the
  dict-membership note below. Counting properly in the presence of `Fraction` or
  `Decimal` values is a non-goal (a compiled port has no such types to price);
  numerical algorithms should use `float`/`CountedFloat` values throughout,
  rather than relying on which side an operand happens to sit.
- counting state is **per OS thread** (created lazily, freed with the thread):
  a `FlopCountingContext` measures only the thread that opened it, is confined
  to that thread while open (cross-thread use raises `RuntimeError`), and
  `PauseFlopCounting` pauses the calling thread only. To measure a
  multi-threaded computation, open one context per worker and sum the results:

  ```python
  def worker(job):
      with FlopCountingContext() as ctx:
          run(job)
      return ctx.flop_counts()

  with ThreadPoolExecutor() as ex:
      total = sum(ex.map(worker, jobs), FlopCounts())
  ```

  All asyncio tasks running on one thread share that thread's counter — there
  is no per-task isolation. Note that while *any* thread has a context open,
  all threads see the patched `math.*` functions (patching is inherently
  process-wide); plain-float calls still take the fast path, and counts always
  land in the thread performing the operation. Free-threaded builds (3.14t) are
  supported and covered by CI; counting there needs no lock, since each thread
  mutates only its own state. Note that the `benchmarking` extra requires **numba
  0.65 or newer** on a free-threaded build — earlier versions ship no
  free-threaded wheels
- builtin `min`/`max` return the winning operand *object*, so with mixed
  counted/plain arguments the result is a plain float whenever a plain constant
  wins — countedness ends silently, and value-dependently: the same call site
  keeps or drops it depending on the data. The comparisons themselves count
  `COMP` correctly; only the result's type can revert, and no dunder exists
  through which `CountedFloat` could intercept the returned object. When the
  result feeds counted computation, re-wrap it — `CountedFloat(min(...))`
  counts nothing (a float-source construction) and is correct whether or not
  the wrap was needed
- dict/set membership of `CountedFloat` keys inflates `COMP`: hash-bucket
  equality checks count as comparisons. This is consistent with the model
  (those comparisons really execute) but can surprise when a dict is used as
  bookkeeping rather than algorithm — pause counting or use plain-float keys
  for bookkeeping structures
- while a `FlopCountingContext` is open, the patched `math.fsum`, `math.prod`,
  `math.sumprod` and `math.dist` materialize their iterable inputs (they call
  `list(...)` on them) even when no `CountedFloat` is involved, so the argument
  can be inspected after the value is computed. The stdlib versions consume some
  of these lazily, so passing a very large one-shot iterator to one of these
  functions inside a context holds the whole sequence in memory — O(n) space
  where the unpatched call would stream. The computed value is unchanged; only
  peak memory differs, and only while a context is active. (`math.hypot` takes
  its coordinates as separate positional arguments, already materialized as a
  tuple by the interpreter, so it does not diverge.)
- flop weights should be taken with a grain of salt and should only provide
  relative ballpark estimates w.r.t. computational complexity. Production
  implementations in a compiled language could have vastly differing
  performance depending on cpu cache sizes, branch prediction misses, compiler
  optimizations using vector operations (AVX etc...), etc...

See also:

- [The counting model](counting_flops.md#the-counting-model-what-gets-counted-and-why)
  — the contract defining what is (and isn't) counted.
- [Math patching semantics](math_patching.md) — which `math` functions are
  instrumented, and the third-party-patching contract.
- [FLOP types reference](flop_types.md) — per-operation lists of what is
  counted and what is not.
