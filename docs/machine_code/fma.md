# FMA

The `FMA` cost is the latency difference between a probe chaining two dependent
`fmadd`s per element and one chaining a single `fmadd` — probes `f_fma_fma` and
`f_fma`. These are the only two probes compiled with FP contraction enabled, so the source's
`tmp * x[i] + x[i]` fuses into a single `fmadd` instruction on both sides.

What Python code counts into `FMA` is described in
[FLOP types](../flop_types.md#flop-fma).

## Inner-loop diff

<!-- BEGIN generated: machine-code-fma-diff -->
```diff
--- f_fma
+++ f_fma_fma
  .L0:
+ ldur  %d0, [%x0, #-16]
+ fmadd  %d1, %d1, %d0, %d0
+ fmadd  %d1, %d0, %d1, %d0
+ stur  %d1, [%x1, #-16]
  ldur  %d0, [%x0, #-8]
  fmadd  %d1, %d1, %d0, %d0
+ fmadd  %d1, %d0, %d1, %d0
  stur  %d1, [%x1, #-8]
- add  %x2, %x2, #2
- ldr  %d0, [%x0], #16
+ ldr  %d0, [%x0]
  fmadd  %d1, %d1, %d0, %d0
- str  %d1, [%x1], #16
+ fmadd  %d1, %d0, %d1, %d0
+ str  %d1, [%x1]
+ ldr  %d0, [%x0, #8]
+ fmadd  %d1, %d1, %d0, %d0
+ fmadd  %d1, %d0, %d1, %d0
+ str  %d1, [%x1, #8]
+ ldr  %d0, [%x0, #16]
+ fmadd  %d1, %d1, %d0, %d0
+ fmadd  %d1, %d0, %d1, %d0
+ str  %d1, [%x1, #16]
+ add  %x0, %x0, #40
+ add  %x1, %x1, #40
+ sub  %x2, %x2, #5
  cmp  %x3, %x2
  b.ne  .L0
```
<!-- END generated: machine-code-fma-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-fma-structure -->
- `f_fma` -- 2 innermost loop(s): 13 instructions, 10 instructions
- `f_fma_fma` -- 2 innermost loop(s): 26 instructions, 7 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_fma`"
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
      fmadd  d1, d1, d2, d2
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
      fmadd  d1, d1, d2, d2
      stur  d1, [x12, #-8]
      add  x11, x11, #2
      ldr  d2, [x13], #16
      fmadd  d1, d1, d2, d2
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

??? note "Full ASM listing: `f_fma_fma`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_12
      subs  x8, x3, #1
      b.lt  LBB0_12
      ldr  x9, [sp, #56]
      ldr  x10, [sp]
      mov  x11, #-3689348814741910324
      movk  x11, #52429
      umulh  x11, x8, x11
      lsr  x11, x11, #2
      add  x11, x11, x11, lsl #2
      sub  x12, x8, x11
      add  x11, x12, #1
      cmp  x11, #5
      csinc  x12, xzr, x12, eq
      sub  x13, x12, x3
      mov  x14, #22377
      movk  x14, #35604, lsl #16
      movk  x14, #48906, lsl #32
      movk  x14, #16389, lsl #48
      fmov  d0, x14
      b  LBB0_4
    LBB0_3:
      subs  x2, x2, #1
      b.le  LBB0_12
    LBB0_4:
      cmp  x8, #4
      b.hs  LBB0_6
      mov  x14, #0
      mov.16b  v1, v0
      b  LBB0_10
    LBB0_6:
      mov  x14, #0
      add  x15, x9, #16
      add  x16, x10, #16
      mov.16b  v1, v0
    LBB0_7:
      ldur  d2, [x16, #-16]
      fmadd  d1, d1, d2, d2
      fmadd  d1, d2, d1, d2
      stur  d1, [x15, #-16]
      ldur  d2, [x16, #-8]
      fmadd  d1, d1, d2, d2
      fmadd  d1, d2, d1, d2
      stur  d1, [x15, #-8]
      ldr  d2, [x16]
      fmadd  d1, d1, d2, d2
      fmadd  d1, d2, d1, d2
      str  d1, [x15]
      ldr  d2, [x16, #8]
      fmadd  d1, d1, d2, d2
      fmadd  d1, d2, d1, d2
      str  d1, [x15, #8]
      ldr  d2, [x16, #16]
      fmadd  d1, d1, d2, d2
      fmadd  d1, d2, d1, d2
      str  d1, [x15, #16]
      add  x16, x16, #40
      add  x15, x15, #40
      sub  x14, x14, #5
      cmp  x13, x14
      b.ne  LBB0_7
      cmp  x11, #5
      b.eq  LBB0_3
      neg  x14, x14
    LBB0_10:
      lsl  x15, x14, #3
      add  x14, x9, x15
      add  x15, x10, x15
      mov  x16, x12
    LBB0_11:
      ldr  d2, [x15], #8
      fmadd  d1, d1, d2, d2
      fmadd  d1, d2, d1, d2
      str  d1, [x14], #8
      subs  x16, x16, #1
      b.ne  LBB0_11
      b  LBB0_3
    LBB0_12:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```
<!-- END generated: machine-code-fma-structure -->

## Discussion

**The subtraction isolates one extra chained `fmadd` per element.**

1. *Intended instruction, and nothing else*: per element, `f_fma_fma` runs two dependent
   `fmadd`s where `f_fma` runs one — visible in the diff as the added
   `+ fmadd …` lines. The many other `-`/`+` pairs are addressing differences between the
   two unrolling shapes (see point 3), not extra work: each element still performs exactly one
   load, the chained arithmetic, and one store on both sides.
2. *In the dependency chain*: both operations read and write the accumulator, so each element
   pays two dependent `fmadd` latencies instead of one; the difference is one.
3. *Loop-structure symmetry*: **not symmetric, deliberately surfaced** — `f_fma` compiles
   2×-unrolled, while `f_fma_fma` compiles 5×-unrolled plus a scalar remainder. The diff therefore aligns loops of
   different unrolling depth, which is what scatters the addressing lines. As on the
   [SQRT page](sqrt.md), both sides serialize through the accumulator, so per-element latency is
   unaffected by unroll depth and the subtraction holds.
