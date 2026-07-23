# Cost-model principles

Every flop weight and every counting decision in `counted-float` answers the same question:
**what does this operation cost?** — and that question has more than one defensible answer
(the code as written, what a compiler would make of it, what the interpreter actually
executes). This page states the rules used to pick one, so that every pricing choice in the
package can name the rule it follows — and the few that deviate can say so explicitly.

## How the imaginary port gets made

Two conventions anchor every rule below.

**First: in counted code, a plain `float` operand is a compile-time
[constant](glossary.md#constant)** — something the imaginary compiled program would know
while being compiled — while a **`CountedFloat` operand is dynamic algorithm input**.
Rules that treat constants specially (strength reduction, reciprocal multiplication) key
on exactly this distinction.

**Second: the port is made in two stages, by two different actors, playing by two
different rules.**

- **The author** — a competent numerical programmer — rewrites the Python code in C. The
  author sees the constants in the source and makes the choices working numerical code
  makes: faced with `x ** 5`, they write the square-and-multiply chain
  (`x2 = x*x; x4 = x2*x2; x4*x`) rather than calling `pow(x, 5.0)`, because that is how
  performance-conscious C code raises to a small constant power. There is no
  bit-exactness bar to clear at this stage, because none *exists*: even the "obvious"
  port that calls libm's `pow` gets different last bits on glibc, Apple's libm and
  Microsoft's UCRT. What the author owes is **algorithmic faithfulness** — the same
  mathematical computation, written the way such code is really written. Every judgment
  call the author is assumed to make is declared in the rules below, together with its
  bound (for exponent chains, `|n| ≤ 16`): a stated, bounded persona — not a claim about
  what all programmers everywhere would do.
- **The compiler** then translates that C source into machine code, and its rule *is*
  mechanical bit-exactness: it may rewrite the source's arithmetic only when the rewrite
  provably never changes any computed value. Replacing `x / 8.0` by `x * 0.125` qualifies
  — the reciprocal is exact, so every result is bit-identical. Fusing `x*y + z` into a
  single fused multiply-add does not: the fused form rounds once where the source rounds
  twice — faster, and slightly *different*. One subtlety is pinned explicitly: on some
  CPUs (notably 64-bit ARM) compilers apply that fusion **by default** at ordinary
  optimization levels, no fast-math flag involved — the model's compiler has it switched
  off (`-ffp-contract=off`), so the priced instruction stream is the same on every
  architecture.

Every pricing decision below is an application of one question: **who produced this
operation — the author, writing it into the source, or the compiler, translating the
source?** Author-written operations are priced as written; compiler rewrites are admitted
only when bit-exact. Whenever the rules mention what real compilers do at plain `-O2`,
that is *corroboration* that an admitted rewrite is real-world practice — never the
admission criterion itself.

## The rules

**Rule 1 — operations that compile to CPU instructions only (no library call) are priced
as a value-preserving [compiled port](glossary.md#compiled-port).**

- **1.1** *(scope)* — covers arithmetic written in operators (`+`, `*`, `%`,
  `round(x, n)`, ...) *and* the named calls that reduce to single instructions
  (`math.sqrt` → `FSQRT`, `abs`/`math.fabs` → `FABS`, `math.copysign`).
- **1.2** *(definition)* — "value-preserving" is the compiler-stage rule from above: the
  emitted machine code computes exactly the values the authored source defines. Any
  rewrite that changes a computed value — whatever fast-math flag or platform default
  would enable it — is out.
- **1.3** *(consequence)* — no [FP contraction](glossary.md#fp-contraction): `x*y + z`
  counts MUL + ADD, not FMA, because fusing is a compiler rewrite that changes values —
  excluded even where it is a platform default (see
  [known limitations](known_limitations.md) for what this over-estimates on real builds).
  The one way to have a fused multiply-add *counted* is to write one: `math.fma(x, y, z)`
  (Python 3.13+) is the author explicitly asking for the fused operation. `fma` can carry
  that meaning because it is special in exactly one way: it has no operator spelling, so
  writing the call is unambiguous intent.
- **1.4** *(consequence)* — [strength reduction](glossary.md#strength-reduction) comes in
  both stages, and the stage decides the test. Bit-exact reductions (`x / 8.0` →
  `x * 0.125`, `x ** 2` → `x * x`) are compiler rewrites, admitted by 1.2. Value-changing
  reductions can only enter as author decisions, declared case by case in the rules below
  — never silently.
- **1.5** *(example)* — constant exponents: `x ** 2` → MUL, `2 ** x` → C99 `exp2`; but
  `10 ** x` → `pow(10, x)`, since `exp10` is not standard C. The square-and-multiply
  chain for `3 ≤ |n| ≤ 16` is the canonical *author* decision: no bit-identity to libm's
  `pow` is owed, because nothing was rewritten — the chain **is** the source the author
  wrote (real compilers agree it is not theirs to make: they only expand `pow` with
  constant exponents beyond 2 under fast-math flags). The `|n| ≤ 16` cutoff bounds the
  claim to exponents where hand-written chains are genuinely how such code gets written;
  beyond it the author calls `pow`, and the generic POW price applies. The reduction keys
  on the constant's *value*, never on the spelling: `math.pow(x, 5.0)` and `x ** 5` are
  two spellings of the same intent and price identically.
- **1.6** *(example)* — reciprocal multiplication for division only where it is exact: a
  power-of-two constant divisor with a finite reciprocal — there, and only there,
  `x * (1/c)` is bit-identical to `x / c`, and compilers apply the fold at plain `-O2` —
  so `x / c` counts MUL for exactly those divisors, and DIV for every other. The one
  stronger fold: `x / 1.0` disappears entirely and counts nothing, like `x ** 1`.
- **1.7** *(example)* — the compiler-stage test also admits the identity folds for
  constant operands: `x * 1.0` and `x - 0.0` fold away entirely, and so does `x + (-0.0)`
  (exact for every `x`); `x * -1.0`, `x / -1.0` and `(-0.0) - x` reduce to a bare sign
  flip and count MINUS. The test is sharp, not sloppy — the near-misses stay counted
  because a signed zero makes them value-*changing*: `x + 0.0` counts ADD (for
  `x = -0.0` the result is `+0.0`, not `x`), `x - (-0.0)` counts SUB (it *is*
  `x + 0.0`), and `0.0 - x` counts SUB (`0.0 - 0.0` gives `+0.0`, where a sign flip
  would give `-0.0`). Inside the decomposed operations the same folds apply to the
  division step: a power-of-two constant divisor turns `x // c`'s and `x % c`'s DIV
  component into MUL.
  *Known deviation: the folds of this bullet are not yet implemented — counted-float
  currently counts `x * 1.0` and `x * -1.0` as MUL, `x - 0.0` and `(-0.0) - x` as SUB,
  `x + (-0.0)` as ADD, `x / -1.0` as MUL (via 1.6), and the decompositions' division step
  as DIV regardless of the divisor.*

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
  regime: huge arguments would put `asinh` in its asymptotic log shortcut (about half the
  general-case cost) and `sin` into its expensive large-argument reduction — extreme
  magnitudes mis-price in either direction.
- **4.4** *(practice)* — where a range needs a non-obvious choice, the benchmark source
  carries a comment saying why.

## Per-type pricing

One row per `FlopType`: the benchmark pair whose latency difference prices it (see
[Benchmark machine code](machine_code/index.md) for the compiled loops behind each pair), the
rule that governs it, and — for grey-zone cases — why the choice is what it is.

<!-- BEGIN generated: cost-model-flop-type-table -->
| Flop type | Weight measured as | Rule | Notes |
|---|---|---|---|
| [`ABS`](machine_code/abs.md) | `f_add_abs` − `f_add` | 1 |  |
| [`ACOS`](machine_code/acos.md) | `f_add_sin_acos` − `f_add_sin` | 2 |  |
| [`ACOSH`](machine_code/acosh.md) | `f_add_acosh` − `f_add` | 2, 4 |  |
| [`ADD`](machine_code/add.md) | `f_add_add` − `f_add` | 1 |  |
| [`ASIN`](machine_code/asin.md) | `f_add_sin_asin` − `f_add_sin` | 2 |  |
| [`ASINH`](machine_code/asinh.md) | `f_add_asinh` − `f_add` | 2, 4 |  |
| [`ATAN`](machine_code/atan.md) | `f_add_atan` − `f_add` | 2, 4 |  |
| [`ATAN2`](machine_code/atan2.md) | `f_add_atan2` − `f_add` | 2, 4 |  |
| [`ATANH`](machine_code/atanh.md) | `f_add_halfsin_atanh` − `f_add_halfsin` | 2 |  |
| [`CBRT`](machine_code/cbrt.md) | `f_add_cbrt` − `f_add` | 2 | numba's `np.cbrt` wraps the libm call in NaN/sign handling CPython's `math.cbrt` never executes, so the probe calls libm through a ctypes binding -- the bare call CPython executes |
| [`COMP`](machine_code/comp.md) | `f_lte_addsub` − `f_add` | 1 | the subtrahend is the ADD/SUB average, and the branchy source compiles branchless -- the weight prices compare-and-select machinery, matching what float comparisons cost in optimized code |
| [`COPYSIGN`](machine_code/copysign.md) | `f_add_copysign` − `f_add` | 1 |  |
| [`COS`](machine_code/cos.md) | `f_add_cos` − `f_add` | 2, 4 |  |
| [`COSH`](machine_code/cosh.md) | `f_add_acosh_cosh` − `f_add_acosh` | 2, 4 |  |
| [`DIST`](machine_code/dist.md) | `f_add_dist2` − `f_add` | 2 | hand-rolled overflow-safe port (no libm `dist` exists); prices the scaled algorithm `math.dist` executes, not a naive sum of squares |
| [`DIST_XARG`](machine_code/dist_xarg.md) | `f_add_dist8` − `f_add_dist2` | 2 | per-extra-coordinate slope of the same overflow-safe port as `DIST` |
| [`DIV`](machine_code/div.md) | `f_div_div` − `f_div` | 1 |  |
| [`ERF`](machine_code/erf.md) | `f_add_erf` − `f_add` | 2, 4 |  |
| [`ERFC`](machine_code/erfc.md) | `f_add_erfc` − `f_add` | 2, 4 |  |
| [`EXP`](machine_code/exp.md) | `f_add_log_exp` − `f_add_log` | 2 |  |
| [`EXP10`](machine_code/exp10.md) | `f_add_log10_exp10` − `f_add_log10` | 2 | `10 ** x` cannot strength-reduce to an `exp10` call -- `exp10` is not standard C -- so a port emits `pow(10, x)`, and that is exactly what the weight measures |
| [`EXP2`](machine_code/exp2.md) | `f_add_log2_exp2` − `f_add_log2` | 2 | `2 ** x` strength-reduces here because a standard-C port emits C99 `exp2`; the weight is measured on the real `exp2` call |
| [`EXPM1`](machine_code/expm1.md) | `f_add_log1p_expm1` − `f_add_log1p` | 2 |  |
| [`FMA`](machine_code/fma.md) | `f_fma_fma` − `f_fma` | 1 |  |
| [`FMOD`](machine_code/fmod.md) | `f_add_fmod` − `f_add` | 2, 4 |  |
| [`GAMMA`](machine_code/gamma.md) | `f_add_gammabase_gamma` − `f_add_gammabase` | 2 |  |
| [`HYPOT`](machine_code/hypot.md) | `f_add_hypot` − `f_add` | 2 | the 2-argument base weight is the real libm call; the hand-rolled scaled probes only supply the per- extra-coordinate slope, validated against this base (within ~10%) |
| [`HYPOT_XARG`](machine_code/hypot_xarg.md) | `f_add_hypot_scaled8` − `f_add_hypot_scaled2` | 2 | hand-rolled overflow-safe port (numba cannot compile n-ary `hypot`); deterministic per-coordinate cost, so rule 2 applies to the port |
| [`LGAMMA`](machine_code/lgamma.md) | `f_add_gammabase_lgamma` − `f_add_gammabase` | 2 |  |
| [`LOG`](machine_code/log.md) | `f_add_log` − `f_add` | 2 |  |
| [`LOG10`](machine_code/log10.md) | `f_add_log10` − `f_add` | 2 |  |
| [`LOG1P`](machine_code/log1p.md) | `f_add_log1p` − `f_add` | 2 |  |
| [`LOG2`](machine_code/log2.md) | `f_add_log2` − `f_add` | 2 |  |
| [`MINUS`](machine_code/minus.md) | `f_add_minus` − `f_add` | 1 |  |
| [`MUL`](machine_code/mul.md) | `f_mul_mul` − `f_mul` | 1 |  |
| [`POW`](machine_code/pow.md) | `f_pow_pow` − `f_pow` | 2 |  |
| [`REMAINDER`](machine_code/remainder.md) | `f_add_remainder` − `f_add` | 2, 4 | numba has no `math.remainder`, so the probe calls libm through a ctypes binding -- still the bare call CPython executes |
| [`RND`](machine_code/rnd.md) | `f_add_round` − `f_add` | 1 |  |
| [`SIN`](machine_code/sin.md) | `f_add_sin` − `f_add` | 2, 4 |  |
| [`SINH`](machine_code/sinh.md) | `f_add_asinh_sinh` − `f_add_asinh` | 2, 4 |  |
| [`SQRT`](machine_code/sqrt.md) | `f_add_sqrt` − `f_add` | 1 |  |
| [`SUB`](machine_code/sub.md) | `f_add_sub` − `f_add` | 1 |  |
| [`SUMPROD`](machine_code/sumprod.md) | `f_add_sumprod2` − `f_add` | 2 | faithful port of CPython's extended-precision (TripleLength) accumulation, error terms emitted through the llvm.fma intrinsic; the 2-element base includes the close-out |
| [`SUMPROD_XELEM`](machine_code/sumprod_xelem.md) | `f_add_sumprod8` − `f_add_sumprod2` | 2 | per-extra-element slope of the same TripleLength port as `SUMPROD` |
| [`TAN`](machine_code/tan.md) | `f_add_tan` − `f_add` | 2, 4 |  |
| [`TANH`](machine_code/tanh.md) | `f_add_tanh` − `f_add` | 2, 4 |  |
| `F2I` | *(no benchmark probe — priced from spec sheets and third-party tables)* | 1 | float→int conversion instruction of the port |
| `I2F` | *(no benchmark probe — priced from spec sheets and third-party tables)* | 1 | int→float conversion instruction of the port |
<!-- END generated: cost-model-flop-type-table -->

## Decomposed operations

Some Python operations have no `FlopType` of their own and count as a composition of the
types above (see [FLOP types](flop_types.md#coverage-at-a-glance) for the full operation
table). Most follow rule 1 at the operation level; `math.fsum` and `round(x, n)` carry
rule 3's documented gaps:

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

`math.dist` and n-ary `math.hypot` are *not* decompositions: they count the dedicated
`DIST` + (n−2) `DIST_XARG` and `HYPOT` + (n−2) `HYPOT_XARG` types, measured on the real
overflow-safe algorithm the calls execute (rule 2).
