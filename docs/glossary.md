# Glossary

Terms used across the reference pages, defined once. Each entry carries a stable anchor for
linking.

## Arity { #arity }

The number of arguments — or elements, for functions taking sequences — a call consumes:
`hypot(x, y, z)` has arity 3, `sumprod` over n-element inputs arity n. The arity-scaled flop
types price such calls as a fixed base weight plus a measured per-extra-argument slope
(`HYPOT` + (n−2) `HYPOT_XARG`, and likewise for `dist` and `sumprod`), instead of one weight
per possible length.

## Benchmark probe { #benchmark-probe }

One of the small numba-compiled functions the flops benchmark times: a doubly-nested loop
feeding one combination of operations through a [dependent chain](#dependent-chain). Each
flop weight is the latency difference between two probes that differ by exactly the
operation being priced. (GPU and HPC literature would call these compute kernels; *probe*
avoids the collision with the operating-system sense of the word.)

## Compiled port { #compiled-port }

The imaginary program the cost model prices: a competent numerical programmer (the
*author*) rewrites the Python code in C, and a compiler translates that C to machine code
without changing any computed value — strict IEEE-754 evaluation, with
[FP contraction](#fp-contraction) pinned off (`-ffp-contract=off`; merely saying
"no fast-math" would not exclude it, since on some targets — aarch64 notably —
contracting is the compiler default at ordinary optimization levels). The two stages obey
different rules: the compiler's arithmetic is bit-exact against the authored source, while
the author's porting choices (which library calls, whether a small constant power becomes
a multiply chain) have no bit-target to hit — different libms already differ in last bits
— and owe algorithmic faithfulness instead. See
[Cost-model principles](cost_model.md#how-the-imaginary-port-gets-made) for the full
story. The
cost model prices operator arithmetic as what this port would execute, rather than what the
much slower Python interpreter happens to do — see
[Cost-model principles](cost_model.md).

## Constant { #constant }

A value the compiled port would know at compile time — a literal, a configuration number —
as opposed to the data the algorithm processes. In counted code the type carries the
distinction: plain `float` operands are treated as constants, `CountedFloat` operands as
dynamic algorithm input. Compilers treat constants specially (see
[strength reduction](#strength-reduction)), and the pricing follows.

## Dependent chain { #dependent-chain }

A sequence of operations where each needs the previous one's result before it can start,
forcing strictly sequential execution — no overlap between consecutive operations. The
benchmarks deliberately feed every measured operation's result into the next iteration,
so they measure [latency](#latency-vs-throughput) rather than the CPU's ability to run
independent operations in parallel.

## Fast path { #fast-path }

A shortcut inside a math function for input regimes where the full computation is
unnecessary. For any argument beyond ±20, `tanh` equals ±1 to machine precision, so the
library returns that constant immediately. Fast paths cost far less than the general case,
so the benchmarks pick input ranges that avoid them: a weight should price the work the
function normally performs, not its shortcut ([cost-model rule 4](cost_model.md#the-rules)).

## FP contraction { #fp-contraction }

A compiler transformation fusing a multiply followed by an add (`x*y + z`) into a single
fused multiply-add instruction. The fused form rounds once instead of twice — faster and
marginally more accurate, but *different*: results no longer match the two separate
operations bit for bit. Since the [compiled port](#compiled-port) must reproduce results
exactly, it does not contract: operator arithmetic counts MUL + ADD, and only the explicit
`math.fma(x, y, z)` counts FMA.

## Latency vs. throughput { #latency-vs-throughput }

Two different answers to "how fast is this operation?". *Latency* is the time from start
until the result is ready; *throughput* is how many such operations complete per unit of
time when the CPU can overlap independent ones — often several times more than latency
suggests. The flop weights are **latency** weights, measured through
[dependent chains](#dependent-chain): they describe the cost seen by an algorithm whose
every step needs the previous step's result.

## libm { #libm }

The C standard math library — the routines (`sin`, `log`, `pow`, ...) shipped with every C
toolchain, and what Python's `math` module calls under the hood. CPUs have no `sin`
instruction; these functions are software routines built from ordinary arithmetic.
Operations in that category are priced by benchmarking the actual libm call.

## Strength reduction { #strength-reduction }

Replacing an expensive operation with a cheaper one that computes the same thing, enabled
when part of the expression is [constant](#constant): `x ** 2` becomes a single multiply,
`x / 2.0` becomes `x * 0.5` (exact, since `0.5` is exactly representable). In the cost
model it happens at either stage of the [compiled port](#compiled-port): bit-exact
reductions are compiler rewrites; value-changing ones (the multiply chain for `x ** 5`)
can only be *author* decisions, declared and bounded in
[cost-model rule 1](cost_model.md#the-rules).
