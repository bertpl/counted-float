# SQRT

The `SQRT` cost is the latency difference between a probe chaining `sqrt(tmp + x[i])` and one
chaining only `tmp + x[i]` — probes `f_add_sqrt` and `f_add`. Exemplar of a **bare arithmetic
instruction**: on ARM64, `math.sqrt` compiles to a single `fsqrt` instruction, not a library call.

What Python code counts into `SQRT` is described in
[FLOP types](../flop_types.md#flop-sqrt).

## Inner-loop diff

<!-- BEGIN generated: machine-code-sqrt-diff -->
```diff
--- f_add
+++ f_add_sqrt
  .L0:
  ldr  %d0, [%x0], #8
  fadd  %d1, %d1, %d0
+ fsqrt  %d1, %d1
  str  %d1, [%x1], #8
  subs  %x2, %x2, #1
  b.ne  .L0
```
<!-- END generated: machine-code-sqrt-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-sqrt-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_sqrt` -- 1 innermost loop(s): 7 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_add`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_11
      subs  x8, x3, #1
      b.lt  LBB0_11
      ldr  x9, [sp, #56]
      ldr  x10, [sp]
      and  x11, x3, #0x7
      and  x12, x3, #0x7ffffffffffffff8
      mov  x13, #22377
      movk  x13, #35604, lsl #16
      movk  x13, #48906, lsl #32
      movk  x13, #16389, lsl #48
      fmov  d0, x13
      b  LBB0_4
    LBB0_3:
      subs  x2, x2, #1
      b.le  LBB0_11
    LBB0_4:
      cmp  x8, #7
      b.hs  LBB0_6
      mov  x13, #0
      mov.16b  v1, v0
      b  LBB0_9
    LBB0_6:
      mov  x13, #0
      add  x14, x10, #32
      add  x15, x9, #32
      mov.16b  v1, v0
    LBB0_7:
      ldur  d2, [x14, #-32]
      fadd  d1, d1, d2
      stur  d1, [x15, #-32]
      ldur  d2, [x14, #-24]
      fadd  d1, d1, d2
      stur  d1, [x15, #-24]
      ldur  d2, [x14, #-16]
      fadd  d1, d1, d2
      stur  d1, [x15, #-16]
      ldur  d2, [x14, #-8]
      fadd  d1, d1, d2
      stur  d1, [x15, #-8]
      ldr  d2, [x14]
      fadd  d1, d1, d2
      str  d1, [x15]
      ldr  d2, [x14, #8]
      fadd  d1, d1, d2
      str  d1, [x15, #8]
      ldr  d2, [x14, #16]
      fadd  d1, d1, d2
      str  d1, [x15, #16]
      ldr  d2, [x14, #24]
      fadd  d1, d1, d2
      str  d1, [x15, #24]
      add  x15, x15, #64
      add  x14, x14, #64
      add  x13, x13, #8
      cmp  x12, x13
      b.ne  LBB0_7
      cbz  x11, LBB0_3
    LBB0_9:
      lsl  x14, x13, #3
      add  x13, x9, x14
      add  x14, x10, x14
      mov  x15, x11
    LBB0_10:
      ldr  d2, [x14], #8
      fadd  d1, d1, d2
      str  d1, [x13], #8
      subs  x15, x15, #1
      b.ne  LBB0_10
      b  LBB0_3
    LBB0_11:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```

??? note "Full ASM listing: `f_add_sqrt`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_6
      cmp  x3, #1
      b.lt  LBB0_6
      ldr  x8, [sp, #56]
      ldr  x9, [sp]
      mov  x10, #22377
      movk  x10, #35604, lsl #16
      movk  x10, #48906, lsl #32
      movk  x10, #16389, lsl #48
      fmov  d0, x10
    LBB0_3:
      mov  x10, x3
      mov  x11, x9
      mov  x12, x8
      mov.16b  v1, v0
    LBB0_4:
      ldr  d2, [x11], #8
      fadd  d1, d1, d2
      fsqrt  d1, d1
      str  d1, [x12], #8
      subs  x10, x10, #1
      b.ne  LBB0_4
      subs  x2, x2, #1
      b.gt  LBB0_3
    LBB0_6:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```
<!-- END generated: machine-code-sqrt-structure -->

## Discussion

**The subtraction isolates exactly one `fsqrt`.**

1. *Intended instruction, and nothing else*: the diff is the single line `+ fsqrt %d1, %d1` —
   loads, stores and loop control are identical on both sides.
2. *In the dependency chain*: `fsqrt` reads and writes `%d1`, the accumulator that feeds the next
   iteration's `fadd`, so each iteration waits for the full add→sqrt latency.
3. *Loop-structure symmetry*: **not symmetric, deliberately surfaced.** `f_add` compiles to an
   8×-unrolled main loop plus a scalar remainder (the diff shows the remainder), while
   `f_add_sqrt` compiles to a single scalar loop. This does not invalidate the measurement: both
   loops serialize through the `%d1` chain, so per-iteration latency is the chained operations'
   latency regardless of unrolling — the unrolled body performs 8 chained iterations' work and
   takes 8 chained iterations' time. But `f_add` is the subtrahend of most derived costs, so a
   toolchain change that alters this unrolling decision *without* preserving the latency-bound
   property would shift the whole weight table — this asymmetry is the primary thing to re-check
   on regeneration.
