# Cost-model rules

Every counting decision in `counted-float` answers one question: **what does this operation cost?** The question has more than one defensible answer — the Python code as written, what a compiler would make of it, what the interpreter actually executes. The model commits to what a compiler would make of it: **it prices your code as an imaginary, competently written C translation** — the [compiled port](glossary.md#compiled-port) — in which every plain operand is a compile-time constant.

The cost model spans three pages, from principle to number:

- **this page** — the contract with the user, what is in scope, and the four pricing rules;
- **[Interpretations](cost_model_interpretations.md)** — where two readings of a rule are defensible, the entry that picks one and says why;
- **[Per-type pricing](cost_model_pricing.md)** — how every flop type's weight is measured, and the operations that count as compositions of them.

## I. The contract { #the-contract }

The model cannot see your source code, so it cannot know which values are your algorithm's input and which are fixed parameters. You declare the difference by type:

- **a `CountedFloat` is dynamic input** — a value the algorithm receives at runtime;
- **a plain operand is a constant** — something a compiled version of your algorithm would know at build time.

A plain operand is therefore eligible for exactly the optimizations real compilers apply to constants. Two consequences of the declaration being *by type*:

- Constant treatment keys on the operand's **value**, never its spelling: an int and an equal-valued float compile identically, and a constant never adds an `I2F` conversion. A plain float that *varies* at runtime is folded on each value it takes — a [stated limitation](known_limitations.md#constant-folding-keys-on-the-operands-value-not-on-it-being-a-literal), not part of the model.
- **`float(x)` is the explicit opt-out**, returning a plain float that ends counting downstream. Safe because leaving the counted world is the visible point of the call.

Counting itself runs per thread, inside an active `FlopCountingContext`:

- **paused** (`PauseFlopCounting`): counts are suppressed, types never are — a paused block hands back `CountedFloat`s that resume counting on exit. That is why `math.*` stays patched while paused — not an implementation detail.
- **outside any context**: `math.*` is unpatched, so type preservation ends at every `math` call on a counted value; the operators preserve the type everywhere. Mechanics in [Math patching semantics](math_patching.md).

## II. What the model prices { #what-the-model-prices }

The model prices operations that **compute on float values** — those whose port emits floating-point instructions or floating-point library calls. Work in any other domain — integer and bit manipulation, string conversion, arbitrary-precision arithmetic — has no `FlopType` and is counted nowhere, by scope rather than by exemption.

How an operation happens to be *implemented* plays no role in that scope question, or anywhere else in the model. `math.copysign` is a value-level floating-point operation and carries a benchmarked weight, whatever bit tricks compute it — and `abs` and unary minus are the same case (the emitted code is an and-mask and an xor); `hex()` reads mantissa nibbles into text and counts nothing, however much it touches a float.

The same scope test places Python's other numeric towers outside the model. `decimal.Decimal`, `fractions.Fraction` and `complex` have no compiled-port counterpart here, so nothing about them is priced:

- converting one **into** the model counts nothing — where an `int` source (bool included) counts the `I2F` its port conversion costs — a stated gap, not an oversight. The same scope test prices every construction route (`CountedFloat(...)`, `from_number`, `fromhex`): int → I2F; float → nothing; `Decimal`, `Fraction` and string parses → nothing; each returns a `CountedFloat`;
- converting **out** (`complex(x)`, `Fraction(x)`), and mixing them into counted arithmetic, ends or bypasses counting; what each mixed operation does today is listed in [known limitations](known_limitations.md#other-limitations).

The same holds one step further out: [numpy is an explicit non-goal](known_limitations.md#numpy-counting-is-an-explicit-non-goal) — its work never flows through the counted type, and its vectorized execution is the throughput regime the latency weights deliberately do not price.

## III. How the port is built { #how-the-port-is-built }

Two actors build the port, and every pricing question reduces to: **who produced this operation — the author, writing it into the source, or the compiler, translating the source?**

- **The author** — a competent numerical programmer — rewrites your Python in C with algorithmic faithfulness: the same computation, written the way performance-conscious numerical code is really written. The author works at the level of *your* code — operators, control flow, calls **into** libraries — and never re-implements a library's internals. Where the author is assumed to make a judgment call, the call is declared and bounded.
- **The compiler** then translates that C into machine code, and its rule is mechanical **bit-exactness**: it may rewrite arithmetic only when the rewrite provably changes no computed value — signed zeros and NaN payloads included — and floating-point contraction is off. One calibration is pinned: IEEE 754 leaves the *sign* of a NaN produced by arithmetic unspecified, so NaN-sign differences sit outside the test — so the sign-flip rewrites are admitted — `x * -1.0` and `(-0.0) - x` both reduce to a bare sign flip, MINUS — alongside the value-exact ones.

Strength reduction exists in both stages, and the stage decides the test: a bit-exact reduction (`x / 8.0` → `x * 0.125`) is a compiler rewrite, admitted by the bit-exactness test alone; a value-changing reduction (the square-and-multiply chain for small constant exponents) can only enter as a declared author decision. What real compilers do at plain `-O2` corroborates that an admitted rewrite is real-world practice — but such corroboration is never the admission criterion.

The result's **type** follows one test, independent of its cost: a float-valued result that depends on a counted operand — at bit level, again signs and NaN payloads included — is a `CountedFloat`, even when it cost nothing to compute (`+x`, `x * 1.0`); a result independent of every counted operand is a plain float (`x ** 0` is `1.0` for every `x`, so the port ships the constant), and downstream folds keyed on it mirror the port's own constant propagation. A container result carries the test per element: `divmod`'s tuple holds two `CountedFloat`s. Cost and countedness are separate axes, and all four combinations occur.

## IV. The rules { #the-rules }

Four rules price every operation, in order of preference. Two defaults span them.

**One operation at a time.** Each operation is priced on its own, from its own operands. The model never sees the expression an operation sits in, so rewrites reaching across neighboring operations — `(x * 2.0) * 4.0` into `x * 8.0`, `-(-x)` into `x` — are outside the model, however bit-exact they are, and both operations are priced. A real compiler makes those rewrites; not making them is a limitation of an instrument that watches operations execute one by one, and the count runs high by however many the compiler would have collapsed.

**A call is priced whole**, whether it is a single-instruction call under rule 1 or a library call under rules 2–3. An operand's value changes a call's price only where a declared interpretation says so — constant `pow` exponents and bases, constant `log` bases, `fma`'s constant product are the declared cases; absent such a declaration, operand values never modify the price of a call that completes. (`math.copysign(x, 2.0)` counts COPYSIGN, not the ABS its constant would make it equivalent to.)

### Rule 1 — CPU instructions: priced as the value-preserving port

Arithmetic written in operators, and the named calls that reduce to single instructions (`math.sqrt`, `abs`, `math.copysign`). The port applies every bit-exact rewrite and no other: `x / 8.0` counts MUL, `x + 0.0` counts ADD (for `x = -0.0` the result is `+0.0`, so the fold would change a bit), and `x*y + z` counts MUL + ADD — fusing is a value-changing rewrite, so the one way to have a fused multiply-add counted is to write one: `math.fma(x, y, z)`. Real builds routinely contract by default; what switching contraction off over-estimates there is noted in [known limitations](known_limitations.md#other-limitations).

Operations that decompose into rule-1 steps — the floored-division family (`//`, `%`, `divmod`), `round(x, n)`'s scale and unscale — fold per step: every step whose operand is a constant (the division step, the remainder's multiply by the divisor, a scale factor of exactly `±1.0`) folds exactly as the written operator would.

### Rule 2 — deterministic library calls: priced by measuring the call

Applies when the call's cost is a fixed number of floating-point operations per invocation (or per element, or per coordinate), independent of the data. The weight is measured, in order of preference:

1. on **the very call**, wherever the benchmark toolchain compiles it (libm's `sin`, `log`, …);
2. on **the bare libm call through a ctypes binding**, where the toolchain's own wrapper would add work CPython never executes;
3. on **a port of the algorithm the call really executes** — overflow-safe scaling and all, never a naive substitute — where neither compiles.

### Rule 3 — input-dependent cost: priced from the documented contract

Where the executing algorithm has no fixed cost to measure (`math.fsum`'s compensation grows with the data), the price is the operation's stated formula, transcribed symbol by symbol into flop types — `math.isclose`'s documented predicate `|a−b| ≤ max(rel_tol·max(|a|,|b|), abs_tol)` becomes SUB + 3 ABS + MUL + 3 COMP. The formula is the *spec*, not anyone's implementation, so no guessing about robust-vs-plain variants arises. The transcription is fixed per call — no guards, no short-circuit savings, whatever branch actually runs — and everything the executing algorithm does differently is a documented gap, never a silent one.

### Rule 4 — benchmark inputs represent the general case

Ranges stay inside the operation's domain, avoid cheap fast paths (`tanh` beyond ±20 saturates), and avoid degenerate regimes that mis-price in either direction (huge arguments put `sin` into its expensive reduction and `asinh` into its cheap asymptotic shortcut). Where a range needs a non-obvious choice, the benchmark source carries a comment saying why.

Every weight is a **latency** weight — measured on a [dependent chain](glossary.md#dependent-chain), the shape numerical algorithms actually execute, or taken from published latencies for the same instruction where no probe exists — never the [throughput](glossary.md#latency-vs-throughput) that independent, overlappable operations could reach. Composite prices follow the same commitment: an operation counted as a composition of flop types adds its parts' latency weights, priced as if the parts chain.

## V. Where countedness ends { #where-countedness-ends }

Counting stops in exactly three places, each one already forced by an earlier section:

- **the result is a constant of the port** — the result-type test in *How the port is built*: a float result independent of every counted operand (`x ** 0`, `1.0 ** x`, `.imag`) comes back plain, because nothing counted remains in it;
- **the value leaves the float domain** — any non-float result (`bool`, `int`, `str`, `complex`, or a value converted into another numeric tower) returns bare, priced where the port pays (`int(x)` counts F2I, `x < y` counts COMP) and priced at nothing where *What the model prices* puts the exit outside the model: string formatting, the complex result of a negative base under a fractional exponent, and every conversion out of the float domain;
- **the user opts out** — `float(x)`, the contract's explicit exit.

Two exits inside the float-domain bullet are priced at nothing by **declared exception** rather than by scope, because the port does emit an instruction for them, and both are labeled where they are documented:

- **truthiness** (`bool(x)`, `if x:`) — the interpreter inserts it implicitly at every `if`, `while`, `and`, `or`, `not` and `assert`, with no opt-out, and `python -O` elides `assert` entirely, so a price here would vary with interpreter flags rather than with the algorithm. The algorithmic spelling `x != 0.0` counts COMP. Documented with [the `COMP` type](flop_types.md#flop-comp).
- **the `%` presentation format** — its scale-by-100 multiply is real, unobservable from Python, and its result cannot re-enter the algorithm; labeled on [the float surface](float_surface.md#the-presentation-contract).

Every other way a counted value goes plain is a **limitation**, not a rule: the operations the instrument cannot count report through the WARNING channel (see [the `math` coverage table](math_patching.md#coverage-of-the-math-module) and [the float surface](float_surface.md#reported-at-warning-verbosity)), and the two interpreter mechanisms the library cannot intercept — the builtins `min`/`max` returning a winning plain constant, and a `Fraction` *winning* the delegation (the reflected operation returning Fraction's own plain float; when Fraction instead hands the arithmetic back to the float operators, they count normally, per *What a count records*) — are stated, with remedies, in [known limitations](known_limitations.md#other-limitations).

A silent plain-float return from a counted operand is neither an exit nor a limitation: it is a defect in the model, not a judgment call.

## VI. What a count records { #what-a-count-records }

Counts record **executed** floating-point work on counted values — wherever it executes — and nothing else:

- every operation computes before it counts, so one that raises registers nothing, at any argument position. Exception paths have no compiled-port counterpart to price anyway: IEEE operations do not trap, so where Python raises on `math.sqrt(-1.0)` or a division by zero, the port returns NaN or infinity and carries on. Where an exception is caught and handled, that port genuinely executed the call that raised — so the count under-states such a path rather than inventing work;
- an operation the counted type declines (`NotImplemented`, after which Python delegates to the other operand or fails) executed no float work and counts nothing — `cf == "abc"` is `False` at zero count, the compare having run nowhere;
- work another routine performs *on* counted values through counted operations registers normally, however deep the call stack — which comparisons a set probe executes, or which guards a stdlib routine runs against a counted operand, is Python's semantics, and the model prices whatever actually ran (the observed outcomes for the stdlib's numeric types are listed in [known limitations](known_limitations.md#other-limitations)).
