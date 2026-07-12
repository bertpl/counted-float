# Known limitations

- currently any non-Python-built-in math operations are not counted (e.g.
  `numpy`)
- not all Python built-in math operations are counted — the remaining gaps are
  the hyperbolic functions (`sinh`/`cosh`/`tanh` and their inverses) and
  `math.copysign`; see the [FLOP types reference](flop_types.md) for the full
  list of what is and isn't counted
- mixed operations with non-float numeric types are outside the counting
  model: `CountedFloat` delegates to the other operand exactly like `float`
  does, so e.g. a `fractions.Fraction` operand generally yields a correct but
  plain — and uncounted — `float` result (downstream counting stops), while a
  `decimal.Decimal` operand raises `TypeError` just as with plain `float`.
  Numerical algorithms should use `float`/`CountedFloat` values throughout.
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
