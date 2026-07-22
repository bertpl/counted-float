# COPYSIGN

The `COPYSIGN` cost is the latency difference between a probe chaining `math.copysign(tmp + x[i], x[i])` and one
chaining only `tmp + x[i]` — probes `f_add_copysign` and `f_add`. On ARM64 this compiles to
a single `bif.16b` (bitwise insert-if-false) instruction, transplanting the sign bit under a constant mask preloaded outside the loop, not a library call.

What Python code counts into `COPYSIGN` is described in
[FLOP types](../flop_types.md#flop-copysign).

## Inner-loop diff

<!-- BEGIN generated: machine-code-copysign-diff -->
```diff
--- f_add
+++ f_add_copysign
  .L0:
  ldr  %d0, [%x0], #8
  fadd  %d1, %d1, %d0
+ bif.16b  %v1, %v0, %v2
  str  %d1, [%x1], #8
  subs  %x2, %x2, #1
  b.ne  .L0
```
<!-- END generated: machine-code-copysign-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-copysign-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_copysign` -- 2 innermost loop(s): 30 instructions, 7 instructions

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

??? note "Full ASM listing: `f_add_copysign`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_11
      subs  x8, x3, #1
      b.lt  LBB0_11
      ldr  x9, [sp, #56]
      ldr  x10, [sp]
      mov  x11, #-6148914691236517206
      movk  x11, #43691
      umulh  x11, x8, x11
      lsr  x11, x11, #2
      mov  w12, #6
      msub  x12, x11, x12, x8
      add  x11, x12, #1
      cmp  x11, #6
      csinc  x12, xzr, x12, eq
      sub  x13, x3, x12
      mov  x14, #22377
      movk  x14, #35604, lsl #16
      movk  x14, #48906, lsl #32
      movk  x14, #16389, lsl #48
      fmov  d0, x14
      movi.2d  v1, #0xffffffffffffffff
      fneg.2d  v1, v1
      b  LBB0_4
    LBB0_3:
      subs  x2, x2, #1
      b.le  LBB0_11
    LBB0_4:
      cmp  x8, #5
      b.hs  LBB0_6
      mov  x14, #0
      mov.16b  v2, v0
      b  LBB0_9
    LBB0_6:
      mov  x14, #0
      add  x15, x9, #24
      add  x16, x10, #24
      mov.16b  v2, v0
    LBB0_7:
      ldur  d3, [x16, #-24]
      fadd  d2, d2, d3
      bif.16b  v2, v3, v1
      stur  d2, [x15, #-24]
      ldur  d3, [x16, #-16]
      fadd  d2, d2, d3
      bif.16b  v2, v3, v1
      stur  d2, [x15, #-16]
      ldur  d3, [x16, #-8]
      fadd  d2, d2, d3
      bif.16b  v2, v3, v1
      stur  d2, [x15, #-8]
      ldr  d3, [x16]
      fadd  d2, d2, d3
      bif.16b  v2, v3, v1
      str  d2, [x15]
      ldr  d3, [x16, #8]
      fadd  d2, d2, d3
      bif.16b  v2, v3, v1
      str  d2, [x15, #8]
      ldr  d3, [x16, #16]
      fadd  d2, d2, d3
      bif.16b  v2, v3, v1
      str  d2, [x15, #16]
      add  x16, x16, #48
      add  x15, x15, #48
      add  x14, x14, #6
      cmp  x13, x14
      b.ne  LBB0_7
      cmp  x11, #6
      b.eq  LBB0_3
    LBB0_9:
      lsl  x15, x14, #3
      add  x14, x9, x15
      add  x15, x10, x15
      mov  x16, x12
    LBB0_10:
      ldr  d3, [x15], #8
      fadd  d2, d2, d3
      bif.16b  v2, v3, v1
      str  d2, [x14], #8
      subs  x16, x16, #1
      b.ne  LBB0_10
      b  LBB0_3
    LBB0_11:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```
<!-- END generated: machine-code-copysign-structure -->

## Discussion

**The subtraction isolates exactly one `bif.16b`.**

1. *Intended instruction, and nothing else*: the diff adds the single line `+ bif.16b …` —
   loads, stores and loop control are otherwise identical.
2. *In the dependency chain*: `bif.16b` reads and writes the accumulator that feeds the next
   iteration's `fadd`, so each iteration waits for the full chain.
3. *Loop-structure symmetry*: **symmetric.** Both probes compile to an 8×-unrolled main loop plus a scalar remainder; the diff shows the two remainders, and the main loops match the same way (one `bif.16b` per element — see the full listings).
