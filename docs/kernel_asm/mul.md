# MUL

The `MUL` cost is the latency difference between a kernel chaining two dependent
`fmul`s per element and one chaining a single `fmul` — kernels `f_mul_mul` and
`f_mul`.

What Python code counts into `MUL` is described in
[FLOP types](../flop_types.md#flop-mul).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-mul-diff -->
```diff
--- f_mul
+++ f_mul_mul
  .L0:
- ldur  %d0, [%x0, #-32]
- fmul  %d1, %d1, %d0
- stur  %d1, [%x1, #-32]
- ldur  %d0, [%x0, #-24]
- fmul  %d1, %d1, %d0
- stur  %d1, [%x1, #-24]
- ldur  %d0, [%x0, #-16]
- fmul  %d1, %d1, %d0
- stur  %d1, [%x1, #-16]
  ldur  %d0, [%x0, #-8]
  fmul  %d1, %d1, %d0
+ fmul  %d1, %d0, %d1
  stur  %d1, [%x1, #-8]
- ldr  %d0, [%x0]
+ add  %x2, %x2, #2
+ ldr  %d0, [%x0], #16
  fmul  %d1, %d1, %d0
- str  %d1, [%x1]
- ldr  %d0, [%x0, #8]
- fmul  %d1, %d1, %d0
- str  %d1, [%x1, #8]
- ldr  %d0, [%x0, #16]
- fmul  %d1, %d1, %d0
- str  %d1, [%x1, #16]
- ldr  %d0, [%x0, #24]
- fmul  %d1, %d1, %d0
- str  %d1, [%x1, #24]
- add  %x1, %x1, #64
- add  %x0, %x0, #64
- add  %x2, %x2, #8
+ fmul  %d1, %d0, %d1
+ str  %d1, [%x1], #16
  cmp  %x3, %x2
  b.ne  .L0
```
<!-- END generated: kernel-asm-mul-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-mul-structure -->
- `f_mul` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_mul_mul` -- 2 innermost loop(s): 14 instructions, 12 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the kernels'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_mul`"
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
      fmul  d1, d1, d2
      stur  d1, [x15, #-32]
      ldur  d2, [x14, #-24]
      fmul  d1, d1, d2
      stur  d1, [x15, #-24]
      ldur  d2, [x14, #-16]
      fmul  d1, d1, d2
      stur  d1, [x15, #-16]
      ldur  d2, [x14, #-8]
      fmul  d1, d1, d2
      stur  d1, [x15, #-8]
      ldr  d2, [x14]
      fmul  d1, d1, d2
      str  d1, [x15]
      ldr  d2, [x14, #8]
      fmul  d1, d1, d2
      str  d1, [x15, #8]
      ldr  d2, [x14, #16]
      fmul  d1, d1, d2
      str  d1, [x15, #16]
      ldr  d2, [x14, #24]
      fmul  d1, d1, d2
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
      fmul  d1, d1, d2
      str  d1, [x13], #8
      subs  x15, x15, #1
      b.ne  LBB0_10
      b  LBB0_3
    LBB0_11:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```

??? note "Full ASM listing: `f_mul_mul`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_10
      cmp  x3, #1
      b.lt  LBB0_10
      ldr  x8, [sp, #56]
      ldr  x9, [sp]
      and  x10, x3, #0x7ffffffffffffffe
      mov  x11, #22377
      movk  x11, #35604, lsl #16
      movk  x11, #48906, lsl #32
      movk  x11, #16389, lsl #48
      fmov  d0, x11
      b  LBB0_6
    LBB0_3:
      mov  x11, #0
      mov.16b  v1, v0
    LBB0_4:
      ldr  d2, [x9, x11, lsl #3]
      fmul  d1, d1, d2
      fmul  d1, d2, d1
      str  d1, [x8, x11, lsl #3]
    LBB0_5:
      subs  x2, x2, #1
      b.le  LBB0_10
    LBB0_6:
      cmp  x3, #1
      b.eq  LBB0_3
      mov  x11, #0
      add  x12, x8, #8
      add  x13, x9, #8
      mov.16b  v1, v0
    LBB0_8:
      ldur  d2, [x13, #-8]
      fmul  d1, d1, d2
      fmul  d1, d2, d1
      stur  d1, [x12, #-8]
      add  x11, x11, #2
      ldr  d2, [x13], #16
      fmul  d1, d1, d2
      fmul  d1, d2, d1
      str  d1, [x12], #16
      cmp  x10, x11
      b.ne  LBB0_8
      tbnz  w3, #0, LBB0_4
      b  LBB0_5
    LBB0_10:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```
<!-- END generated: kernel-asm-mul-structure -->

## Discussion

**The subtraction isolates one extra chained `fmul` per element.**

1. *Intended instruction, and nothing else*: per element, `f_mul_mul` runs two dependent
   `fmul`s where `f_mul` runs one — visible in the diff as the added
   `+ fmul …` lines. The many other `-`/`+` pairs are addressing differences between the
   two unrolling shapes (see point 3), not extra work: each element still performs exactly one
   load, the chained arithmetic, and one store on both sides.
2. *In the dependency chain*: both operations read and write the accumulator, so each element
   pays two dependent `fmul` latencies instead of one; the difference is one.
3. *Loop-structure symmetry*: **not symmetric, deliberately surfaced** — `f_mul` compiles
   to an 8×-unrolled main loop plus a scalar remainder, while `f_mul_mul` compiles 2×-unrolled. The diff therefore aligns loops of
   different unrolling depth, which is what scatters the addressing lines. As on the
   [SQRT page](sqrt.md), both sides serialize through the accumulator, so per-element latency is
   unaffected by unroll depth and the subtraction holds.
