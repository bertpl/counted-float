# Benchmark kernel machine code

Every benchmarked flop weight is a measured latency *difference* between two compiled kernels: a
kernel containing the operation of interest, minus a kernel identical except for that operation.
The pages in this section show the machine code behind each of those differences, so you can see
for yourself exactly what a weight does — and does not — include: the compiled inner loops of the
two kernels as a unified diff, each kernel's loop structure, and the complete compiled functions.
Nothing about a weight is reduced to trust.

Each page closes with a short discussion walking through what the listings show:

1. **What the diff isolates** — the intended instruction (or call), and whatever else changed
   with it.
2. **Where it sits in the dependency chain** the kernel serializes through — the measurement is
   designed to capture latency, not throughput.
3. **How the loop structures compare** — unrolling or vectorization differences that would move
   loop overhead between the two sides.

## Pages

<!-- BEGIN generated: kernel-asm-page-list -->
**Hardware instructions**

- [ABS](abs.md)
- [ADD](add.md)
- [COMP](comp.md)
- [COPYSIGN](copysign.md)
- [DIV](div.md)
- [FMA](fma.md)
- [MINUS](minus.md)
- [MUL](mul.md)
- [RND](rnd.md)
- [SQRT](sqrt.md)
- [SUB](sub.md)

**Library calls (libm)**

- [ACOS](acos.md)
- [ACOSH](acosh.md)
- [ASIN](asin.md)
- [ASINH](asinh.md)
- [ATAN](atan.md)
- [ATAN2](atan2.md)
- [ATANH](atanh.md)
- [CBRT](cbrt.md)
- [COS](cos.md)
- [COSH](cosh.md)
- [ERF](erf.md)
- [ERFC](erfc.md)
- [EXP](exp.md)
- [EXP10](exp10.md)
- [EXP2](exp2.md)
- [EXPM1](expm1.md)
- [FMOD](fmod.md)
- [GAMMA](gamma.md)
- [HYPOT](hypot.md)
- [LGAMMA](lgamma.md)
- [LOG](log.md)
- [LOG10](log10.md)
- [LOG1P](log1p.md)
- [LOG2](log2.md)
- [POW](pow.md)
- [REMAINDER](remainder.md)
- [SIN](sin.md)
- [SINH](sinh.md)
- [TAN](tan.md)
- [TANH](tanh.md)

**Arity-scaled algorithms**

- [DIST](dist.md)
- [DIST_XARG](dist_xarg.md)
- [HYPOT_XARG](hypot_xarg.md)
<!-- END generated: kernel-asm-page-list -->

## How to read the listings

- **Architecture: ARM64 (Apple M-series).** Machine code is architecture-specific, so the
  committed listings are generated on one architecture only. What a weight measures is decided by
  the kernel pair, and that shows on any single target.
- **The diff shows inner loops.** Full-function dumps are dominated by prologue and setup code
  that runs once rather than inside the timed loop, so the diff compares *innermost* loops of the
  two kernels' compiled native functions. The compiler may turn one source loop into several
  innermost loops (e.g. an 8×-unrolled main loop plus a scalar remainder loop) — each page
  inventories all of them, and the diff shows the best-matching pair across the two kernels. The
  complete compiled functions are included in collapsed listings on each page.
- **Registers and labels are canonicalized** (renamed in order of first appearance, e.g. `%x0`,
  `%d1`, `.L0`) before diffing, so a diff line always means a structural difference — never the
  register allocator picking different names for the same code. One side effect: when one kernel
  holds an extra live register, every later register gets a shifted canonical index, so an
  otherwise-identical line can show as a `-`/`+` pair differing only in those indices. The
  discussions call this out where it happens.

The listings are regenerated from the compiled kernels and committed; the prose discussions are
written against them.
