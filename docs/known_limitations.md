# Known limitations

## numpy counting is an explicit non-goal

The counting model prices scalar code as a compiled port would execute it;
array operations are bulk kernels outside that model, and no part of numpy's
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

## Other limitations

- a few Python built-in math operations remain uncounted — the special
  functions (`gamma`, `lgamma`, `erf`, `erfc`) and the float-representation
  helpers (`remainder`, `frexp`, `ldexp`, `modf`, `nextafter`, `ulp`); see the
  [`math` coverage table](math_patching.md#coverage-of-the-math-module) for
  the full per-function status and the
  [FLOP types reference](flop_types.md) for per-operation counting rules. A
  counting context can be asked to report such calls as it meets them, so a
  count that is quietly missing them says so — see
  [watching what gets counted](counting_flops.md#watching-what-gets-counted)
- operator-level fused multiply-add is not modeled: `a*b + c` counts as separate
  MUL + ADD, but a compiled port on any modern target (x86 FMA3, ARMv8) commonly
  fuses it into a single FMA instruction with a single rounding, so flop counts
  over-estimate fusable multiply-add sequences (dot products, Horner evaluation).
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
  `float`, in either order. Numerical algorithms should use
  `float`/`CountedFloat` values throughout, rather than relying on which side an
  operand happens to sit.
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
  mutates only its own state. Note that the `numba` extra requires **numba
  0.65 or newer** on a free-threaded build — earlier versions ship no
  free-threaded wheels
- dict/set membership of `CountedFloat` keys inflates `COMP`: hash-bucket
  equality checks count as comparisons. This is consistent with the model
  (those comparisons really execute) but can surprise when a dict is used as
  bookkeeping rather than algorithm — pause counting or use plain-float keys
  for bookkeeping structures
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
