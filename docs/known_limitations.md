# Known limitations

- currently any non-Python-built-in math operations are not counted (e.g.
  `numpy`)
- not all Python built-in math operations are counted (e.g. hyperbolic
  functions)
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
