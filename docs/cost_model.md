# Cost-model principles

Every flop weight and every counting decision in `counted-float` answers the same question:
**what does this operation cost?** — and that question has more than one defensible answer
(the code as written, what a compiler would make of it, what the interpreter actually
executes). This page states the rules used to pick one, so that every pricing choice in the
package can name the rule it follows — and the few that deviate can say so explicitly.

One convention underlies everything below: in counted code, a **plain `float` operand is a
compile-time [constant](glossary.md#constant)** — something the hypothetical compiled
program would know while being compiled — while a **`CountedFloat` operand is dynamic
algorithm input**. Rules that depend on an operand being constant (strength reduction,
reciprocal multiplication) key on exactly this distinction.

## The rules

**Rule 1 — operations that compile to CPU instructions only (no library call) are priced
as a value-preserving [compiled port](glossary.md#compiled-port).**

- **1.1** *(scope)* — covers arithmetic written in operators (`+`, `*`, `%`,
  `round(x, n)`, ...) *and* the named calls that reduce to single instructions
  (`math.sqrt` → `FSQRT`, `abs`/`math.fabs` → `FABS`, `math.copysign`).
- **1.2** *(definition)* — "value-preserving" means the port must produce bit-identical
  results; transformations a compiler only applies under fast-math flags are out.
- **1.3** *(consequence)* — no FP [contraction](glossary.md#fp-contraction): `x*y + z`
  counts MUL + ADD, not FMA — fusing changes rounding.
- **1.4** *(consequence)* — [strength reduction](glossary.md#strength-reduction) applies
  only where the reduced form is value-identical *and* is what a standard-C port genuinely
  emits.
- **1.5** *(example)* — constant exponents: `x ** 2` → MUL, `2 ** x` → C99 `exp2`; but
  `10 ** x` → `pow(10, x)`, since `exp10` is not standard C.
- **1.6** *(example)* — reciprocal multiplication for division only where it is exact: a
  power-of-two constant divisor with a finite reciprocal — there, and only there,
  `x * (1/c)` is bit-identical to `x / c`, and compilers apply the fold at plain `-O2` —
  so `x / c` counts MUL for exactly those divisors, and DIV for every other. The one
  stronger fold: `x / 1.0` disappears entirely and counts nothing, like `x ** 1`.

**Rule 2 — operations that compile to a library call are priced as the call's real
algorithm, contract included.**

- **2.1** *(scope)* — applies whenever the call's cost is *deterministic per call*: a
  fixed number of operations per invocation (or per element or coordinate), independent
  of the data values. Anything else falls to rule 3.
- **2.2** *(consequence)* — the weight is measured on the very call wherever the
  toolchain can compile it ([libm](glossary.md#libm)'s `sin`, `log`, ...).
- **2.3** *(nuance)* — where the toolchain cannot compile the real call, a faithful port
  of the algorithm it executes is benchmarked instead — never a naive substitute
  (`math.dist`'s overflow-safe scaling, not a plain sum of squares).
- **2.4** *(nuance)* — regime-dependent [fast paths](glossary.md#fast-path) inside such
  functions are handled by rule 4's input ranges, not by pricing the shortcut.

**Rule 3 — operations whose real algorithm has input-dependent cost are priced as their
deterministic mathematical core, with the gap stated.**

- **3.1** *(example)* — `math.fsum` maintains as many non-overlapping partial sums as the
  *values* force (mixing widely different magnitudes grows the list, cancellation shrinks
  it), so even for a fixed-length input there is no constant to benchmark; it is priced as
  the mathematical reduction, (n−1) ADD.
- **3.2** *(consequence)* — the un-priced machinery is stated explicitly wherever the
  price is documented: a deviation under this rule is a documented gap, never a silent
  one.

**Rule 4 — benchmark inputs represent the operation's general case.**

- **4.1** *(consequence)* — input ranges stay inside the operation's domain.
- **4.2** *(consequence)* — input ranges avoid cheap fast paths (saturation shortcuts,
  early returns — e.g. `tanh` beyond ±20, `erf` beyond ±6), so a weight prices the real
  computation rather than a shortcut.
- **4.3** *(consequence)* — input ranges represent the general-case cost, not a degenerate
  regime.
- **4.4** *(practice)* — where a range needs a non-obvious choice, the benchmark source
  carries a comment saying why.

## Per-type pricing

One row per `FlopType`: the benchmark pair whose latency difference prices it (see
[Benchmark machine code](kernel_asm/index.md) for the compiled loops behind each pair), the
rule that governs it, and — for grey-zone cases — why the choice is what it is.

<!-- BEGIN generated: cost-model-flop-type-table -->
| Flop type | Weight measured as | Rule | Notes |
|---|---|---|---|
| [`ABS`](kernel_asm/abs.md) | `f_add_abs` − `f_add` | 1 |  |
| [`ACOS`](kernel_asm/acos.md) | `f_add_sin_acos` − `f_add_sin` | 2 |  |
| [`ACOSH`](kernel_asm/acosh.md) | `f_add_acosh` − `f_add` | 2, 4 |  |
| [`ADD`](kernel_asm/add.md) | `f_add_add` − `f_add` | 1 |  |
| [`ASIN`](kernel_asm/asin.md) | `f_add_sin_asin` − `f_add_sin` | 2 |  |
| [`ASINH`](kernel_asm/asinh.md) | `f_add_asinh` − `f_add` | 2, 4 |  |
| [`ATAN`](kernel_asm/atan.md) | `f_add_atan` − `f_add` | 2, 4 |  |
| [`ATAN2`](kernel_asm/atan2.md) | `f_add_atan2` − `f_add` | 2, 4 |  |
| [`ATANH`](kernel_asm/atanh.md) | `f_add_halfsin_atanh` − `f_add_halfsin` | 2 |  |
| [`CBRT`](kernel_asm/cbrt.md) | `f_add_cbrt` − `f_add` | 2 | numba's `np.cbrt` wraps the libm call in NaN/sign handling CPython's `math.cbrt` never executes, so the kernel calls libm through a ctypes binding -- the bare call CPython executes |
| [`COMP`](kernel_asm/comp.md) | `f_lte_addsub` − `f_add` | 1 | the subtrahend is the ADD/SUB average, and the branchy source compiles branchless -- the weight prices compare-and-select machinery, matching what float comparisons cost in optimized code |
| [`COPYSIGN`](kernel_asm/copysign.md) | `f_add_copysign` − `f_add` | 1 |  |
| [`COS`](kernel_asm/cos.md) | `f_add_cos` − `f_add` | 2, 4 |  |
| [`COSH`](kernel_asm/cosh.md) | `f_add_acosh_cosh` − `f_add_acosh` | 2, 4 |  |
| [`DIST`](kernel_asm/dist.md) | `f_add_dist2` − `f_add` | 2 | hand-rolled overflow-safe port (no libm `dist` exists); prices the scaled algorithm `math.dist` executes, not a naive sum of squares |
| [`DIST_XARG`](kernel_asm/dist_xarg.md) | `f_add_dist8` − `f_add_dist2` | 2 | per-extra-coordinate slope of the same overflow-safe port as `DIST` |
| [`DIV`](kernel_asm/div.md) | `f_div_div` − `f_div` | 1 |  |
| [`ERF`](kernel_asm/erf.md) | `f_add_erf` − `f_add` | 2, 4 |  |
| [`ERFC`](kernel_asm/erfc.md) | `f_add_erfc` − `f_add` | 2, 4 |  |
| [`EXP`](kernel_asm/exp.md) | `f_add_log_exp` − `f_add_log` | 2 |  |
| [`EXP10`](kernel_asm/exp10.md) | `f_add_log10_exp10` − `f_add_log10` | 2 | `10 ** x` cannot strength-reduce to an `exp10` call -- `exp10` is not standard C -- so a port emits `pow(10, x)`, and that is exactly what the weight measures |
| [`EXP2`](kernel_asm/exp2.md) | `f_add_log2_exp2` − `f_add_log2` | 2 | `2 ** x` strength-reduces here because a standard-C port emits C99 `exp2`; the weight is measured on the real `exp2` call |
| [`EXPM1`](kernel_asm/expm1.md) | `f_add_log1p_expm1` − `f_add_log1p` | 2 |  |
| [`FMA`](kernel_asm/fma.md) | `f_fma_fma` − `f_fma` | 1 |  |
| [`FMOD`](kernel_asm/fmod.md) | `f_add_fmod` − `f_add` | 2, 4 |  |
| [`GAMMA`](kernel_asm/gamma.md) | `f_add_gammabase_gamma` − `f_add_gammabase` | 2 |  |
| [`HYPOT`](kernel_asm/hypot.md) | `f_add_hypot` − `f_add` | 2 | the 2-argument base weight is the real libm call; the hand-rolled scaled kernels only supply the per- extra-coordinate slope, validated against this base (within ~10%) |
| [`HYPOT_XARG`](kernel_asm/hypot_xarg.md) | `f_add_hypot_scaled8` − `f_add_hypot_scaled2` | 2 | hand-rolled overflow-safe port (numba cannot compile n-ary `hypot`); deterministic per-coordinate cost, so rule 2 applies to the port |
| [`LGAMMA`](kernel_asm/lgamma.md) | `f_add_gammabase_lgamma` − `f_add_gammabase` | 2 |  |
| [`LOG`](kernel_asm/log.md) | `f_add_log` − `f_add` | 2 |  |
| [`LOG10`](kernel_asm/log10.md) | `f_add_log10` − `f_add` | 2 |  |
| [`LOG1P`](kernel_asm/log1p.md) | `f_add_log1p` − `f_add` | 2 |  |
| [`LOG2`](kernel_asm/log2.md) | `f_add_log2` − `f_add` | 2 |  |
| [`MINUS`](kernel_asm/minus.md) | `f_add_minus` − `f_add` | 1 |  |
| [`MUL`](kernel_asm/mul.md) | `f_mul_mul` − `f_mul` | 1 |  |
| [`POW`](kernel_asm/pow.md) | `f_pow_pow` − `f_pow` | 2 |  |
| [`REMAINDER`](kernel_asm/remainder.md) | `f_add_remainder` − `f_add` | 2, 4 | numba has no `math.remainder`, so the kernel calls libm through a ctypes binding -- still the bare call CPython executes |
| [`RND`](kernel_asm/rnd.md) | `f_add_round` − `f_add` | 1 |  |
| [`SIN`](kernel_asm/sin.md) | `f_add_sin` − `f_add` | 2, 4 |  |
| [`SINH`](kernel_asm/sinh.md) | `f_add_asinh_sinh` − `f_add_asinh` | 2, 4 |  |
| [`SQRT`](kernel_asm/sqrt.md) | `f_add_sqrt` − `f_add` | 1 |  |
| [`SUB`](kernel_asm/sub.md) | `f_add_sub` − `f_add` | 1 |  |
| [`TAN`](kernel_asm/tan.md) | `f_add_tan` − `f_add` | 2, 4 |  |
| [`TANH`](kernel_asm/tanh.md) | `f_add_tanh` − `f_add` | 2, 4 |  |
| `F2I` | *(no benchmark kernel — priced from spec sheets and third-party tables)* | 1 | float→int conversion instruction of the port |
| `I2F` | *(no benchmark kernel — priced from spec sheets and third-party tables)* | 1 | int→float conversion instruction of the port |
<!-- END generated: cost-model-flop-type-table -->

## Decomposed operations

Some Python operations have no `FlopType` of their own and count as a composition of the
types above (see [FLOP types](flop_types.md#coverage-at-a-glance) for the full operation
table). Most follow rule 1 at the operation level; the last two entries are **known
deviations** from the rule that governs them, stated here explicitly:

- `x // y` → DIV + RND, `x % y` / `divmod` → DIV + RND + MUL + SUB — the floored-division
  sequences a port emits.
- `round(x, n)` with nonzero `n` → MUL + RND + DIV — scale into the digit position, round,
  scale back (the unscale is a true divide: the power-of-ten scale factor has no exact
  reciprocal, so rule 1.6's fold does not apply). Stated gap under rule 3: CPython itself
  computes this via correctly-rounded decimal conversion, whose input-dependent machinery
  is knowingly not modeled.
- `math.degrees` / `math.radians` → MUL, `math.prod` → one MUL per chained multiply.
- `math.fsum` → (n−1) ADD under rule 3: the compensation machinery is input-dependent and
  knowingly not modeled.
- `math.dist` → n SUB + n MUL + (n−1) ADD + SQRT. *Known deviation from rule 2: the
  counting uses this naive decomposition even though the `DIST`/`DIST_XARG` weights
  measuring the real overflow-safe algorithm are already benchmarked — the two layers
  currently disagree.*
- `math.hypot` with 3+ arguments → n MUL + (n−1) ADD + SQRT. *Known deviation from rule 2,
  same situation as `math.dist`: the `HYPOT`/`HYPOT_XARG` weights exist, the counting does
  not use them yet.* (The 2-argument form counts `HYPOT` and follows rule 2.)
