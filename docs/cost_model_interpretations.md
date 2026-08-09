# Cost-model interpretations

A few places in the [rules](cost_model_rules.md) admit two defensible readings. Each entry below resolves one such place: the **tension** (what two readings the rules allow), the **interpretation** (the one the model uses), and **why** (the principle that decides it).

Entries are cited as `rule 2 · measurement-fallbacks`, here and in code. Slugs are frozen — entries are appended, never renamed — so every citation and anchor stays valid.

## fma-stays-as-written

**Tension.** Bit-exactness admits one direction of the fused multiply-add and not the other. Fusing `x*y + z` changes values (one rounding where the source has two), but *unfusing* a written `fma(x, 1.0, z)` is bit-exact — it computes exactly `x + z` — and real compilers diverge on it at `-O2` (clang rewrites to a plain add, gcc keeps the fused instruction). So does a written `math.fma` with degenerate constants unfuse?

**Interpretation.** The written form decides both directions: operators never fuse, and a `math.fma` call never unfuses — once an fma survives, constant operand values are not inspected. The one prior question is whether an fma survives at all: with *both* multiplicands plain, no fused instruction remains — the constant product folds at compile time, leaving an ADD (or nothing, when the product is exactly `-0.0`). That is ordinary rule-1 constant folding, not an unfusing.

**Why.** `math.fma` is special in exactly one way: it has no operator spelling, so writing the call is unambiguous author intent asking for the fused instruction. Pricing the author's written arithmetic — fused stays fused, unfused stays unfused — is fixed for the same reason as the model's compiler having [floating-point contraction](glossary.md#fp-contraction) switched off (`-ffp-contract=off`: the compiler never fuses a written `x*y + z` on its own), and for the same reason: the priced instruction stream comes out identical on every architecture and toolchain.

## exponent-chain-bound

**Tension.** A constant integer exponent can in principle expand to a square-and-multiply chain at any size — `x ** 5` and `x ** 500` are the same construction. Where does the author stop writing chains and call `pow`?

**Interpretation.** The full constant-exponent ladder, keyed on value (so `math.pow(x, 5.0)` with a plain `5.0` and `x ** 5` price identically). The ladder prices float-domain results only: where the operation leaves the float domain — a negative base under a fractional exponent, whose result is `complex` — the rules page's exit list governs instead, and nothing is counted, whichever operand is counted.

- `0` → nothing, and a plain result: `pow(x, 0)` is `1.0` for every `x` by the standards the rules page cites, so the port ships a constant;
- `1` → nothing — `pow(x, 1)` is `x` bit-exactly, the compiler-stage identity;
- `-1` → DIV — the author writes the reciprocal `1.0 / x`;
- `±0.5` → SQRT / SQRT + DIV — declared author decisions, and genuinely value-changing ones: `pow(-0.0, 0.5)` is `+0.0` where `sqrt(-0.0)` is `-0.0`, so the compiler stage could never make them;
- integer `2 ≤ |n| ≤ 16` → the square-and-multiply chain (`x ** 5` → 3 MUL; negative exponents add one DIV);
- anything else → generic POW.

A `CountedFloat` exponent is runtime input, not a constant, so no rung of the ladder applies to it: with a counted base too, the call prices POW; with a constant base, the base ladder in [exp10-is-pow](#exp10-is-pow) governs instead (`2 ** cf` prices EXP2, not POW).

**Why.** The chain is an author decision, not a compiler rewrite — it needs no bit-identity to libm's `pow`, because nothing was rewritten: the chain *is* the source the author would write. Real compilers agree the choice is not theirs (they expand constant exponents beyond 2 only under fast-math flags). The bound keeps the author's declared decision defensible: within it, hand-written chains are how performance-conscious code genuinely raises to small constant powers; beyond it, that claim stops being true and the author calls `pow`.

## classifiers-price-their-question

**Tension.** The float classifiers (`math.isnan`, `isinf`, `isfinite`, `isnormal`, `issubnormal`, `signbit`) come out free if the two actors are followed strictly: the author calls the C99 macro — never re-implements it — and the compiler lowers the macro to integer bit tests (`isfinite` does on both priced architectures), and integer work is outside the model's scope. Read strictly, every classifier prices at zero. Two things break under that reading:

- **the same argument would zero out rule 1's prices for the whole sign family**: `fabs` compiles to an and-mask, unary minus to an xor, `copysign` to two bitwise ops;
- **identical questions would price differently by spelling**: `math.isnan(x)` free, while `x != x` — the same question written as an operator — unavoidably counts COMP.

**Interpretation.** Classifiers are priced as value-level float operations — the boundary drawn in *What the model prices*, the same one that gives `math.copysign` its benchmarked weight — on the floating-point canonical form of the question each asks, whatever lowering a particular compiler picks:

- `isnan` → COMP, the self-compare `x != x`;
- `isinf` → ABS + COMP, the test `|x| = ∞`;
- `isfinite` → ABS + COMP, the test `|x| < ∞`;
- `isnormal` and `issubnormal` → ABS + 2 COMP, two bounds on one magnitude.

`signbit` is the one classifier whose question has no floating-point formula — `x < 0.0` is not it (`signbit(-0.0)` is `True` where `-0.0 < 0.0` is `False`), and the faithful `copysign(1.0, x) < 0.0` needs its copysign solely to make the sign visible to a comparison — so it charges only the bool-exit compare every classifier's question ends in: one COMP, the spelling's copysign unpriced.

**Why.** A zero price fails both ways the tension names, and it under-states real cost: extracting a bool from a float value crosses from the FP register file to flags at latencies in the compare-and-select class — exactly the machinery the COMP weight measures (on x86, `isnan` typically compiles to the FP self-compare itself). Pricing the canonical question keeps one price per operation across spellings and architectures; pricing signbit's copysign would charge for how its question must be phrased in float arithmetic, not for what it asks. The fixed per-call price of the two range predicates (`isnormal`, `issubnormal`) over-charges inputs where a chained Python spelling would short-circuit — that gap is owned by [formula-price-is-fixed](#formula-price-is-fixed).

## exp10-is-pow

**Tension.** `2 ** x` strength-reduces to a real `exp2` call, so symmetry suggests `10 ** x` reduces to `exp10`.

**Interpretation.** `2 ** x` prices as C99 `exp2`, measured on the real call. `10 ** x` prices as `pow(10, x)` — and the EXP10 weight is *measured* on `pow(10, x)`, so the weight measures the call the name describes. Any other constant base — `math.e` included — prices generic POW: no exponential reduction is declared for it, and `pow(e, x)` is not `exp(x)` bit-wise, so the compiler stage could not make one.

**Why.** The author writes portable standard C, and calls into libraries at their public surface: `exp2` is standard C99, `exp10` is not. A strength reduction to a call the port cannot portably make would price an instruction stream the port cannot emit.

EXP10 still exists as its own flop type — rather than the call simply counting POW — because `10 ** x` is its own operation with its own general case: the base is pinned at 10, so libm's `pow` runs the same internal regime on every call, and rule 4 prices an operation on *its* general case. The weight is measured on exactly that fixed-base `pow(10, x)` call — the type names what the user wrote, the measurement what the port emits. Generic POW's weight prices the two-runtime-operand regime instead.

## log-constant-base-folds

**Tension.** `math.log(x, c)` with a constant base: the port computes `log(x) / log(c)`, and `log(c)` folding to a compile-time constant is the two actors doing their ordinary work — no interpretation needed there. The open question is the division that remains: rewriting `log(x) / LOG_C` into `log(x) * (1/LOG_C)` is **not** bit-exact (`1/log(c)` is almost never exactly representable), so the compiler stage is forbidden from making that rewrite — by exactly the rule [reciprocal-exactness-bound](#reciprocal-exactness-bound) states. LOG + DIV and LOG + MUL are both defensible ports.

**Interpretation.** The author writes the multiply form: precompute `C = 1/log(c)` at build time, emit `log(x) * C` — LOG + MUL. The folded constant is then an ordinary constant multiplier, so the `±1.0` folds apply to it:

- constant base 2 or 10 → LOG2 / LOG10: the port calls those directly, skipping the division;
- base `e`, where `C` is exactly `1.0` → LOG alone, the multiply folding away;
- base `1/e`, where `C` is exactly `-1.0` → LOG + MINUS;
- any other constant base → LOG + MUL;
- a *counted* base → LOG per counted operand plus DIV, a runtime reciprocal costing the division it would save.

The form presupposes that `C` exists: a base of exactly `1.0` has `log(c) = 0` and no reciprocal, and CPython raises before completing the call, so nothing is counted there.

**Why.** A declared author decision, on the same footing as the exponent chain: precomputing the inverse log of a constant base and multiplying per element is how performance-conscious C genuinely writes repeated base-`c` logarithms. It is deliberately *not* the compiler-stage reciprocal fold — that one stays bit-exact and power-of-two-only ([reciprocal-exactness-bound](#reciprocal-exactness-bound)); this one is the author trading last-bit identity for a multiply, declared here.

## identity-folds-are-sign-exact

**Tension.** Rule 1 admits every bit-exact rewrite, which sorts the constant-operand identities into three groups — but which group a case lands in is not visible from the expression. `x + 0.0` and `x + (-0.0)` look like one fold, as do `x * 1.0` and `x * -1.0`, and a reader applying the test by eye will either fold all of them or none.

**Interpretation.** Signed zero decides every case, and the three groups are:

| Expression (constant operand) | Counts | Why |
|---|---|---|
| `x * 1.0` · `x - 0.0` · `x + (-0.0)` | nothing | each is exactly `x` for every `x`, `-0.0` included |
| `x * -1.0` · `x / -1.0` · `(-0.0) - x` | MINUS | exactly `-x` for every `x`, so the port emits a bare sign flip |
| `x + 0.0` · `x - (-0.0)` · `0.0 - x` | ADD · SUB · SUB | value-changing at `x = -0.0`, where each gives `+0.0` |

The same folds reach the constant-operand steps of a decomposition: `x % 1.0` drops the `c·⌊x/c⌋` multiply, `x % -1.0` turns that multiply into MINUS, and the division step of each routes through [reciprocal-exactness-bound](#reciprocal-exactness-bound) on its own. Division by other constants is [reciprocal-exactness-bound](#reciprocal-exactness-bound)'s; the exponent and log ladders are their own entries.

**Why.** The bit-exactness test is sharp rather than approximate, and at these operands the whole question is a single zero's sign: `-0.0 + 0.0` is `+0.0`, so folding `x + 0.0` to `x` would change a result the port must reproduce, while `x + (-0.0)` changes nothing for any `x`. The sign-flip group survives the same test on the NaN-sign calibration the rules page states — the sign of an arithmetic NaN is unspecified, so it is not a value the rewrite has to preserve.

## reciprocal-exactness-bound

**Tension.** Division by a constant classically rewrites to multiplication by its reciprocal. Bit-exactness admits the rewrite for some constants only — which?

**Interpretation.** `x / c` counts MUL for exactly the power-of-two divisors of either sign whose reciprocal is finite — `|c| ≥ 2^-1023` — and DIV for every other constant. The two strongest folds sit at `±1.0`: `x / 1.0` disappears entirely, `x / -1.0` is a bare sign flip (MINUS). The same routing applies wherever a division step appears inside a decomposition (`x // c`, `x % c`, `divmod`).

**Why.** Powers of two are the only values whose reciprocal is exactly representable, and below `2^-1023` the reciprocal overflows to infinity — the rewrite would change values, so bit-exactness rejects it. Inside the admitted set, compilers apply the fold at plain `-O2` (corroboration, as always, not criterion). The bound binds the *compiler* stage only: an author may still replace a constant division by a multiply as a declared, value-changing decision — [log-constant-base-folds](#log-constant-base-folds) is the one current instance.

## fmax-shares-comp-weight

**Tension.** For `math.fmax` / `fmin` the two actors give a clear answer: the author calls the C99 function, and the compiler emits — on ARM — a single IEEE max/min instruction (`fmaxnm` / `fminnm`), and on x86, which has no IEEE-semantics max instruction (`maxsd` returns its second operand under NaN), a short branchless compare-select sequence with a NaN fixup. The open question is rule 2's: read literally, "measure the very call" gives fmax and fmin a benchmarked flop type of their own — yet the machinery the port executes is the same compare-and-select class the COMP weight already measures.

**Interpretation.** No new type: one COMP per call, the COMP weight reused the way `math.fabs` reuses ABS. The NaN-quieting fixup is declared here as this pricing's stated gap — the price charges the selection, not the quieting. The semantics stay distinct from the builtins `min` / `max` (order-dependent comparison chains returning whichever operand survives): shared machinery and a shared price, never shared meaning.

**Why.** A flop type earns its place when its machinery differs measurably from every existing type's. fmax's port occupies exactly COMP's class — on ARM literally one instruction of it — so a dedicated weight would re-measure a known number under a new name, at the full cost of a type (benchmark probes, spec-sheet rows, a row on every weights surface) for no added information.

## measurement-fallbacks

**Tension.** Rule 2 says the weight is measured on the very call, but the numba-based benchmark toolchain cannot always compile the exact call CPython executes.

**Interpretation.** The preference order is: the very call; the bare libm call through a ctypes binding; a hand-written port of the algorithm the call really executes. The current assignments (deliberately enumerated — the set is irregular, and the list is the checklist):

- **ctypes libm**: CBRT (the toolchain's `cbrt` wraps libm in NaN/sign handling CPython never executes) and REMAINDER (the toolchain has no `math.remainder`);
- **hand-written ports**: DIST and HYPOT_XARG (the overflow-safe scaled algorithms; no n-ary libm call exists to compile) and SUMPROD (CPython's extended-precision accumulation, error terms via the fma intrinsic);
- **anchored mix**: HYPOT's two-argument base weight is the real libm call; the hand-rolled scaled probes supply only the per-extra-coordinate slope, validated against that base.

**Why.** The weight must price the algorithm CPython actually runs. Each fallback is the nearest measurable stand-in for exactly that — the bare call CPython links, or a faithful port of its documented algorithm — never a naive substitute, which rule 2 forbids.

## formula-price-is-fixed

**Tension.** Rule 3 transcribes a documented formula, but the executing implementation guards, short-circuits, and respells. Is the price conditioned on the branch the call actually takes?

**Interpretation.** No: the transcription is charged unconditionally, per call.

- `math.isclose` counts SUB + 3 ABS + MUL + 3 COMP on every regime, infinities included — the equality and infinity guards, the short-circuit savings, and the implementation's two-multiply respelling are all outside the price.
- `math.fsum` counts (n−1) ADD while the real compensation machinery grows and shrinks with the data.
- The range classifiers (`isnormal`, `issubnormal`) charge their fixed ABS + 2 COMP even on inputs where a chained Python spelling stops after one compare.

**Why.** A formula contains no control flow by construction, so its transcription is the one fixed-cost object an input-dependent operation offers — conditioning the price on branches would reintroduce exactly the input-dependence rule 3 exists to escape. The obligation that comes with the fixed price: every divergence of the executing algorithm is stated where the price is documented — a documented gap, never a silent one.

## loops-do-not-fold

**Tension.** A call over a sequence decomposes into ordinary operations — `math.prod` into multiplies — so rule 1's per-step folds look like they should apply, making a `1.0` element free and a plain prefix cost nothing. But a call is written as `prod(seq)` precisely when the chain cannot be written out: the sequence is long, or its length is only known at runtime.

**Interpretation.** Such a call prices by its element count alone, and no element folds. `math.prod` counts (n−1) MUL for n elements where `start` is the multiplicative identity — a port seeds its accumulator from the first element, and the identity keys on *value* like every other constant, so a `1` passed explicitly folds exactly as the default does — and n MUL where `start` is counted, or is a plain value other than 1. The call prices only if some element or the start is counted; a sequence of plain floats is ordinary constant arithmetic and counts nothing.

The price is registered once, for the whole call. A call that raises part-way therefore registers nothing, however many elements it consumed first — the loop is one priced operation, not n of them.

The boundary against the folds that do apply is where the constant sits: a constant **written at the call site as an operand** folds (`x % 1.0`, `x ** 5`, `log(x, 3)`, `round(x, 2)`); an **element of a sequence the call iterates** does not. The call form decides, not whether some call site happens to pass a literal.

**Why.** The port is a loop over an array, and its body is one instruction executed once per element — it runs whatever value the element holds, and no compiler constant-propagates through a traversal. Pricing the folds would claim an unrolled port that the call form itself denies, and the error is unbounded: `prod([cf] + [1.0] * 999)` would count nothing where the port executes 999 multiplies.

`math.fsum` reaches the same flat shape from the other direction — rule 3, because its compensated summation has no fixed cost to measure — so the two agree without sharing a rule. And the built-in `sum`, along with any loop written by hand, cannot be priced this way at all: it is not interceptable, so its counts come from the individual operator calls and fold accordingly. That gap, and the two ways to work around it, are stated in [known limitations](known_limitations.md#loops-the-library-cannot-count-as-loops).

## decompositions-sum-latencies

**Tension.** An operation priced as a composition of flop types — a rule-3 transcription (`isclose` → SUB + 3 ABS + MUL + 3 COMP) or a rule-1 decomposition (`x % y` → DIV + RND + MUL + SUB) — could be priced two ways: the sum of the parts' latency weights, as if every part waits for the previous one, or a critical-path model of the real dependency graph. The parts are demonstrably not always chained: `isclose`'s `|a-b|` and its `rel_tol · max(|a|, |b|)` branch are independent subtrees a superscalar core overlaps, and `isnormal`'s two compares share one magnitude. Other decompositions are inherently serial — the exponent chain, `round(x, n)`'s scale → round → unscale — so the gap between the two readings is case-dependent.

**Interpretation.** Always the sum, for every composite price — transcriptions and decompositions alike. Where the real port overlaps independent parts, the sum over-states, and that over-statement is declared here once, for all composite prices.

**Why.** Modeling the overlap would need per-architecture scheduling knowledge the model refuses everywhere else — one price per operation, on every architecture, is a standing commitment. The weights themselves are measured on dependent chains, so the chained sum is the only composition consistent with what a weight *is*. And the bias is one-directional: within the latency framework the sum is the price of the fully-chained case, never an under-statement — the same declared-gap spirit as the range predicates' short-circuit over-charge in [formula-price-is-fixed](#formula-price-is-fixed).
