# Known limitations

- currently any non-Python-built-in math operations are not counted (e.g.
  `numpy`)
- a few Python built-in math operations remain uncounted — notably
  `math.copysign`; see the
  [`math` coverage table](math_patching.md#coverage-of-the-math-module) for
  the full per-function status and the
  [FLOP types reference](flop_types.md) for per-operation counting rules
- mixed operations with non-float numeric types are outside the counting
  model: `CountedFloat` delegates to the other operand exactly like `float`
  does, so e.g. a `fractions.Fraction` operand generally yields a correct but
  plain — and uncounted — `float` result (downstream counting stops), while a
  `decimal.Decimal` operand raises `TypeError` just as with plain `float`.
  Numerical algorithms should use `float`/`CountedFloat` values throughout.
- counting state is process-global and **not thread-safe or async-safe**:
  concurrent counted computations interfere with each other's counts (and on
  free-threaded Python builds concurrent increments can be lost), so run one
  counted algorithm at a time
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
