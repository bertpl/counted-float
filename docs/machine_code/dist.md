# DIST

The `DIST` cost is the per-call base price of `math.dist`, measured as the latency difference
between a probe chaining the overflow-safe scaled distance of two 2-D points and one chaining
only `tmp + x[i]` — probes `f_add_dist2` and `f_add`. Together with
[DIST_XARG](dist_xarg.md) (the per-extra-coordinate slope) it prices `dist` at any
dimensionality. The probe hand-rolls the scaled algorithm a faithful `math.dist` port
executes: per-coordinate deltas, scaling by the largest magnitude so no square overflows, then
`sqrt` and rescale. Why the overflow-safe flavor is the one being priced is covered in the [benchmark design rationale](../analysis_methodology.md#16-benchmark-design-rationale).

## Inner-loop diff

<!-- BEGIN generated: machine-code-dist-diff -->
```diff
--- f_add
+++ f_add_dist2
  .L0:
- ldr  %d0, [%x0], #8
+ ldp  %d0, %d1, [%x0, #-8]
+ fadd  %d1, %d2, %d1
+ ldur  %d3, [%x0, #-16]
+ fabd  %d2, %d1, %d0
+ fabd  %d4, %d0, %d3
+ fcmp  %d4, %d2
+ fcsel  %d2, %d4, %d2, gt
+ fcmp  %d2, #0.0
+ b.eq  .L1
+ fsub  %d1, %d1, %d0
+ fsub  %d0, %d0, %d3
+ fdiv  %d3, %d5, %d2
+ fmul  %d1, %d1, %d3
+ fmul  %d0, %d0, %d3
+ fmul  %d1, %d1, %d1
+ fmul  %d0, %d0, %d0
  fadd  %d1, %d1, %d0
- str  %d1, [%x1], #8
+ fsqrt  %d1, %d1
+ fmul  %d2, %d2, %d1
+ str  %d2, [%x1], #8
+ add  %x0, %x0, #8
  subs  %x2, %x2, #1
  b.ne  .L0
```
<!-- END generated: machine-code-dist-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-dist-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_dist2` -- 3 innermost loop(s): 25 instructions, 60 instructions, 24 instructions

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

??? note "Full ASM listing: `f_add_dist2`"
    ```asm
      .cfi_startproc
      cmp  x2, #1
      b.lt  LBB0_6
      cmp  x3, #1
      b.lt  LBB0_6
      ldr  x8, [sp, #56]
      ldp  x10, x9, [sp]
      sub  x11, x10, #8
      sub  x12, x10, #16
      cmp  x3, #1
      b.ne  LBB0_7
      add  x13, x2, #1
      mov  x14, #22377
      movk  x14, #35604, lsl #16
      movk  x14, #48906, lsl #32
      movk  x14, #16389, lsl #48
      fmov  d0, x14
      fmov  d1, #1.00000000
    LBB0_4:
      ldr  d2, [x10]
      ldr  d3, [x11, x9, lsl #3]
      ldr  d4, [x12, x9, lsl #3]
      fadd  d5, d2, d0
      fabd  d2, d5, d3
      fabd  d6, d3, d4
      fcmp  d6, d2
      fcsel  d2, d6, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_15
      fsub  d5, d5, d3
      fsub  d3, d3, d4
      fdiv  d4, d1, d2
      fmul  d5, d5, d4
      fmul  d3, d3, d4
      fmul  d4, d5, d5
      fmul  d3, d3, d3
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x8]
      sub  x13, x13, #1
      cmp  x13, #1
      b.gt  LBB0_4
    LBB0_6:
      str  xzr, [x0]
      mov  w0, #0
      ret
    LBB0_7:
      mov  x13, #22377
      movk  x13, #35604, lsl #16
      movk  x13, #48906, lsl #32
      movk  x13, #16389, lsl #48
      fmov  d0, x13
      fmov  d1, #1.00000000
      b  LBB0_9
    LBB0_8:
      cmp  x2, #1
      sub  x2, x2, #1
      b.le  LBB0_6
    LBB0_9:
      ldr  d2, [x10]
      ldr  d3, [x11, x9, lsl #3]
      ldr  d4, [x12, x9, lsl #3]
      fadd  d5, d2, d0
      fabd  d2, d5, d3
      fabd  d6, d3, d4
      fcmp  d6, d2
      fcsel  d2, d6, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_15
      fsub  d5, d5, d3
      fsub  d3, d3, d4
      fdiv  d4, d1, d2
      fmul  d5, d5, d4
      fmul  d3, d3, d4
      fmul  d4, d5, d5
      fmul  d3, d3, d3
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x8]
      ldp  d3, d5, [x10]
      ldr  d4, [x11, x9, lsl #3]
      fadd  d5, d2, d5
      fabd  d2, d5, d3
      fabd  d6, d3, d4
      fcmp  d6, d2
      fcsel  d2, d6, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_15
      fsub  d5, d5, d3
      fsub  d3, d3, d4
      fdiv  d4, d1, d2
      fmul  d5, d5, d4
      fmul  d3, d3, d4
      fmul  d4, d5, d5
      fmul  d3, d3, d3
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x8, #8]
      cmp  x3, #2
      b.eq  LBB0_8
      sub  x13, x3, #2
      add  x14, x10, #16
      add  x15, x8, #16
    LBB0_13:
      ldp  d4, d3, [x14, #-8]
      fadd  d3, d2, d3
      ldur  d5, [x14, #-16]
      fabd  d2, d3, d4
      fabd  d6, d4, d5
      fcmp  d6, d2
      fcsel  d2, d6, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_15
      fsub  d3, d3, d4
      fsub  d4, d4, d5
      fdiv  d5, d1, d2
      fmul  d3, d3, d5
      fmul  d4, d4, d5
      fmul  d3, d3, d3
      fmul  d4, d4, d4
      fadd  d3, d3, d4
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x15], #8
      add  x14, x14, #8
      subs  x13, x13, #1
      b.ne  LBB0_13
      b  LBB0_8
    LBB0_15:
    Lloh0:
      adrp  x8, _.const.picklebuf.<addr>@GOTPAGE
    Lloh1:
      ldr  x8, [x8, _.const.picklebuf.<addr>@GOTPAGEOFF]
      str  x8, [x1]
      mov  w0, #1
      ret
      .loh AdrpLdrGot  Lloh0, Lloh1
      .cfi_endproc
    ```
<!-- END generated: machine-code-dist-structure -->

## Discussion

**The subtraction isolates the whole 2-coordinate scaled-distance computation — inline code,
no library call.**

1. *What the diff shows*: on top of `f_add`'s load/`fadd` skeleton, the additions are the
   algorithm itself: the coordinate deltas and the max-magnitude scan — where LLVM fused each
   `fsub`+`fabs` pair into a single `fabd` (absolute-difference) instruction — then the
   zero-guard (`fcmp #0.0`, protecting the division when both deltas are zero), the reciprocal
   `fdiv`, per-coordinate `fmul`/square/accumulate, `fsqrt`, and the rescaling `fmul`. One
   extra load fetches the second point's coordinates.
2. *In the dependency chain*: the max-scan (`fcmp`/`fcsel`), the `fdiv`, the accumulation and
   the `fsqrt` serialize, and the rescaled result feeds the next iteration's first delta — the
   whole algorithm sits in the measured chain.
3. *Loop-structure symmetry*: `f_add` unrolls 8×; the dist loop, carrying the zero-guard
   branch, cannot unroll — the guard's rotated variants are why the inventory lists several
   regions for it. As on the [SQRT page](sqrt.md), both sides remain latency-bound, so the
   subtraction holds.
