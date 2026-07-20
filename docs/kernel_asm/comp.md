# COMP

The `COMP` cost prices a floating-point compare. Its kernel, `f_lte_addsub`, chains
`tmp = tmp - x[i]` **or** `tmp = tmp + x[i]` depending on `tmp >= x[i]` — a compare steering
between an add and a subtract. Since add and subtract cost the same but are not free, the
subtrahend is the *average* of the single-`ADD` and single-`SUB` kernels' latencies; the diff
below shows `f_add` (the `SUB` kernel differs from it by one opcode only).

What Python code counts into `COMP` is described in
[FLOP types](../flop_types.md#flop-comp).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-comp-diff -->
```diff
--- f_add
+++ f_lte_addsub
  .L0:
  ldr  %d0, [%x0], #8
- fadd  %d1, %d1, %d0
- str  %d1, [%x1], #8
+ fneg  %d1, %d0
+ fcmp  %d2, %d0
+ fcsel  %d0, %d1, %d0, ge
+ fadd  %d2, %d2, %d0
+ str  %d2, [%x1], #8
  subs  %x2, %x2, #1
  b.ne  .L0
```
<!-- END generated: kernel-asm-comp-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-comp-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_lte_addsub` -- 1 innermost loop(s): 9 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the kernels'
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

??? note "Full ASM listing: `f_lte_addsub`"
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
      fneg  d3, d2
      fcmp  d1, d2
      fcsel  d2, d3, d2, ge
      fadd  d1, d1, d2
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
<!-- END generated: kernel-asm-comp-structure -->

## Discussion

**The subtraction isolates the compare-and-select machinery — `fcmp` + `fcsel` (+ an
input-side `fneg`).**

1. *What the diff shows*: LLVM compiled the source-level branch **branchless** — instead of two
   loop bodies, it negates the element up front (`fneg`), compares (`fcmp`), selects the operand
   (`fcsel`), and always adds. Subtracting the add/sub average therefore leaves
   `fcmp` + `fcsel` + `fneg` as the priced work — a faithful stand-in for what float-comparison
   control flow costs in optimized code.
2. *In the dependency chain*: `fcmp` reads the accumulator, `fcsel` waits on the flags, and the
   `fadd` waits on `fcsel`, so compare and select sit squarely in the serialized chain. The
   `fneg` runs on the freshly loaded element, off the chain, overlapping earlier work.
3. *Loop-structure symmetry*: `f_add` unrolls 8×, the branchy kernel does not; as on the
   [SQRT page](sqrt.md), both sides remain latency-bound so the subtraction holds.
