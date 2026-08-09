# Per-type pricing

Every flop type's weight, how it is measured, and the operations that count as compositions of the types. The [rules](cost_model_rules.md) say why each price is what it is; the [interpretations](cost_model_interpretations.md) resolve the grey zones the notes below cite; the measured weight *values* live with the [built-in data](builtin_data.md) and the per-type [machine-code pages](machine_code/index.md).

Every weight is a **latency** weight: the latency difference between two [dependent-chain](glossary.md#dependent-chain) benchmark probes whose loops differ by the operation being priced — or, for the two conversion instructions no probe reaches, a published latency for that instruction. Per-extra-argument weights divide the difference by the number of arguments separating the two probes. Composite prices below add their parts' weights as if the parts chain — the declared bias of `rule 4 · decompositions-sum-latencies`.

## The flop types

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
| [`COMP`](machine_code/comp.md) | `f_lte_addsub` − `f_add` | 1 | the subtrahend is the ADD/SUB average, and the branchy source compiles branchless -- the weight prices compare-and-select machinery, matching what float comparisons cost in optimized code. `math.fmax`/`fmin` reuse this weight: their port -- the IEEE max/min instruction (ARM's `fmaxnm`/`fminnm`) -- is one instruction of the same compare-select class, the same reuse as `math.fabs` -> ABS. They stay a different value function from the builtin `min`/`max` (NaN-quieting selection vs a comparison chain returning whichever operand survives, order-dependent under NaN): shared machinery, and so a shared price, not shared semantics |
| [`COPYSIGN`](machine_code/copysign.md) | `f_add_copysign` − `f_add` | 1 |  |
| [`COS`](machine_code/cos.md) | `f_add_cos` − `f_add` | 2, 4 |  |
| [`COSH`](machine_code/cosh.md) | `f_add_acosh_cosh` − `f_add_acosh` | 2, 4 |  |
| [`DIST`](machine_code/dist.md) | `f_add_dist2` − `f_add` | 2 | hand-rolled overflow-safe port (no libm `dist` exists); prices the scaled algorithm `math.dist` executes, not a naive sum of squares |
| [`DIST_XARG`](machine_code/dist_xarg.md) | (`f_add_dist8` − `f_add_dist2`) / 6 | 2 | per-extra-coordinate slope of the same overflow-safe port as `DIST` |
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
| [`HYPOT_XARG`](machine_code/hypot_xarg.md) | (`f_add_hypot_scaled8` − `f_add_hypot_scaled2`) / 6 | 2 | hand-rolled overflow-safe port (numba cannot compile n-ary `hypot`); deterministic per-coordinate cost, so rule 2 applies to the port |
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
| [`SUMPROD_XELEM`](machine_code/sumprod_xelem.md) | (`f_add_sumprod8` − `f_add_sumprod2`) / 6 | 2 | per-extra-element slope of the same TripleLength port as `SUMPROD` |
| [`TAN`](machine_code/tan.md) | `f_add_tan` − `f_add` | 2, 4 |  |
| [`TANH`](machine_code/tanh.md) | `f_add_tanh` − `f_add` | 2, 4 |  |
| `F2I` | *(no benchmark probe — priced from spec sheets and third-party tables)* | 1 | float→int conversion instruction of the port |
| `I2F` | *(no benchmark probe — priced from spec sheets and third-party tables)* | 1 | int→float conversion instruction of the port |
<!-- END generated: cost-model-flop-type-table -->

## Decomposed operations

Operations with no flop type of their own count as compositions of the types above, each citing the rule and interpretation that fix it. Every composite price on this page adds its parts as if they chain (`decompositions-sum-latencies`).

**Floored division** (rule 1; constant steps fold per the rules page):

- `x // y` → DIV + RND (the floor is a float→float round, not an F2I);
- `x % y` and `divmod(x, y)` → DIV + RND + MUL + SUB — divmod shares the quotient's floor with the remainder, so it costs the same as a lone `%`.

**The round family** (rule 1; the n ≠ 0 form carries a rule-3 gap):

- `round(x)` → F2I, returning `int`;
- `round(x, 0)` → RND, returning `CountedFloat`;
- `round(x, n ≠ 0)` → MUL + RND + DIV — scale into the digit position, round, scale back; the unscale is a true divide (a power-of-ten factor has no exact reciprocal). Two stated gaps: CPython itself computes this via correctly-rounded decimal conversion, whose input-dependent machinery is knowingly not modeled; and the scale-and-unscale port is the price at every `n`, including magnitudes beyond ~308 where the scale factor is not a finite double and no author would write that port.

**Float→int exits** (rule 1): `int(x)`, `math.floor`, `math.ceil`, `math.trunc` → F2I each.

**The classifiers** (rule 3 · classifiers-price-their-question):

- `math.isnan` → COMP;
- `math.isinf`, `math.isfinite` → ABS + COMP each;
- `math.isnormal`, `math.issubnormal` → ABS + 2 COMP each;
- `math.signbit` → COMP.

**Formula-priced calls** (rule 3 · formula-price-is-fixed):

- `math.isclose` → SUB + 3 ABS + MUL + 3 COMP;
- `math.fsum` → (n−1) ADD, where n is the number of elements passed, counted or not.

**Sequence calls** (rule 1 · loops-do-not-fold): `math.prod` → (n−1) MUL for n elements, n for a `start` that is counted or whose value is not 1 — no element folds, because the port's loop body runs once per element whatever it holds. Like every price on this page it applies only where a counted value is involved; a sequence of plain floats counts nothing. The built-in `sum` is not interceptable and does fold, costing n ADD for n counted values and less when plain elements come first; the workarounds are in [known limitations](known_limitations.md#loops-the-library-cannot-count-as-loops).

**Single-instruction respellings** (rule 1):

- `math.degrees`, `math.radians` → MUL each, the conversion factor folding to a constant;
- `float.is_integer` → RND + COMP, the counted spelling `x // 1.0 == x` — RND rather than F2I, because no int ever materializes.

**Constant operands** — a constant exponent, base or logarithm base changes what the port emits. Those ladders are enumerated where they are decided: [exponent-chain-bound](cost_model_interpretations.md#exponent-chain-bound), [exp10-is-pow](cost_model_interpretations.md#exp10-is-pow) and [log-constant-base-folds](cost_model_interpretations.md#log-constant-base-folds).

## Arity-scaled operations

At two or more arguments, `math.hypot`, `math.dist` and `math.sumprod` are **not** decompositions: they count dedicated types measured on the real algorithms the calls execute (rule 2 · measurement-fallbacks). The single-argument forms take the shortcut the call itself takes, which is a composition of ordinary types.

| Operation | Counts |
|---|---|
| `hypot`, n ≥ 2 arguments | HYPOT + (n−2) HYPOT_XARG |
| `hypot`, 1 argument | ABS — the call computes \|x\|, and a port emits `fabs` |
| `dist`, n ≥ 2 dimensions | DIST + (n−2) DIST_XARG |
| `dist`, 1-D | SUB + ABS — the single-coordinate shortcut, not the scaled machinery |
| `sumprod`, n ≥ 2 elements | SUMPROD + (n−2) SUMPROD_XELEM |
| `sumprod`, 1 element | SUMPROD — the base alone |

The base weights are measured on two-argument probes, so a one-element `sumprod` pays a base that includes work a second element would have shared; the slope is not subtracted below the base. `hypot` and `dist` avoid the question by taking their own single-argument shortcuts.
