# HYPOT_XARG

The `HYPOT_XARG` cost is the per-extra-coordinate slope of the overflow-safe scaled `hypot`
algorithm: the latency difference between its 8-coordinate and 2-coordinate forms — kernels
`f_add_hypot_scaled8` and `f_add_hypot_scaled2` — divided by the 6 extra coordinates. Exemplar of
an **arity-scaled pair**: the two sides are not "same loop ± one instruction" but the same
algorithm at two sizes, so the diff is expected to be large — what must hold is that every added
line belongs to the six extra coordinates and their scaling, and nothing shared changed shape. Why the slope is measured on a hand-rolled overflow-safe port is covered in the [benchmark design rationale](../analysis_methodology.md#16-benchmark-design-rationale).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-hypot-xarg-diff -->
```diff
--- f_add_hypot_scaled2
+++ f_add_hypot_scaled8
  .L0:
- ldp  %d0, %d1, [%x0, #-8]
- fadd  %d1, %d2, %d1
- fabs  %d2, %d1
+ ldp  %d0, %d1, [%x0, #48]
+ fadd  %d2, %d2, %d1
+ fabs  %d1, %d2
  fabs  %d3, %d0
- fcmp  %d3, %d2
- fcsel  %d2, %d3, %d2, gt
- fcmp  %d2, #0.0
+ fcmp  %d3, %d1
+ fcsel  %d4, %d3, %d1, gt
+ ldp  %d3, %d1, [%x0, #32]
+ fabs  %d5, %d1
+ fcmp  %d5, %d4
+ fcsel  %d4, %d5, %d4, gt
+ fabs  %d5, %d3
+ fcmp  %d5, %d4
+ fcsel  %d6, %d5, %d4, gt
+ ldp  %d5, %d4, [%x0, #16]
+ fabs  %d7, %d4
+ fcmp  %d7, %d6
+ fcsel  %d7, %d7, %d6, gt
+ fabs  %d8, %d5
+ fcmp  %d8, %d7
+ ldr  %d6, [%x1, #8]!
+ fcsel  %d7, %d8, %d7, gt
+ fabs  %d8, %d6
+ fcmp  %d8, %d7
+ fcsel  %d7, %d8, %d7, gt
+ cmp  %x2, #7
+ csel  %x3, %x4, xzr, lo
+ ldr  %d8, [%x0, %x3, lsl #3]
+ fabs  %d9, %d8
+ fcmp  %d9, %d7
+ fcsel  %d7, %d9, %d7, gt
+ fcmp  %d7, #0.0
  b.eq  .L1
- fdiv  %d3, %d4, %d2
- fmul  %d1, %d1, %d3
- fmul  %d0, %d0, %d3
- fmul  %d1, %d1, %d1
+ fdiv  %d9, %d10, %d7
+ fmul  %d2, %d2, %d9
+ fmul  %d2, %d2, %d2
+ fmul  %d0, %d0, %d9
  fmul  %d0, %d0, %d0
- fadd  %d0, %d1, %d0
+ fadd  %d0, %d2, %d0
+ fmul  %d2, %d1, %d9
+ fmul  %d2, %d2, %d2
+ fadd  %d0, %d2, %d0
+ fmul  %d2, %d3, %d9
+ fmul  %d2, %d2, %d2
+ fadd  %d0, %d2, %d0
+ fmul  %d2, %d4, %d9
+ fmul  %d2, %d2, %d2
+ fadd  %d0, %d2, %d0
+ fmul  %d2, %d5, %d9
+ fmul  %d2, %d2, %d2
+ fadd  %d0, %d2, %d0
+ fmul  %d2, %d6, %d9
+ fmul  %d2, %d2, %d2
+ fadd  %d0, %d2, %d0
+ fmul  %d2, %d8, %d9
+ fmul  %d2, %d2, %d2
+ fadd  %d0, %d2, %d0
  fsqrt  %d0, %d0
- fmul  %d2, %d2, %d0
- str  %d2, [%x1], #8
- add  %x0, %x0, #8
- subs  %x2, %x2, #1
+ fmul  %d2, %d7, %d0
+ str  %d2, [%x5, %x2, lsl #3]
+ add  %x2, %x2, #1
+ mov  %x0, %x1
+ cmp  %x6, %x2
  b.ne  .L0
```
<!-- END generated: kernel-asm-hypot-xarg-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-hypot-xarg-structure -->
- `f_add_hypot_scaled2` -- 2 innermost loop(s): 22 instructions, 21 instructions
- `f_add_hypot_scaled8` -- 2 innermost loop(s): 67 instructions, 64 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the kernels'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_add_hypot_scaled2`"
    ```asm
      .cfi_startproc
      cmp  x2, #1
      b.lt  LBB0_6
      cmp  x3, #1
      b.lt  LBB0_6
      ldr  x8, [sp, #56]
      ldp  x10, x9, [sp]
      sub  x11, x10, #8
      subs  x12, x3, #1
      b.ne  LBB0_7
      add  x12, x2, #1
      mov  x13, #22377
      movk  x13, #35604, lsl #16
      movk  x13, #48906, lsl #32
      movk  x13, #16389, lsl #48
      fmov  d0, x13
      fmov  d1, #1.00000000
    LBB0_4:
      ldr  d3, [x10]
      ldr  d2, [x11, x9, lsl #3]
      fadd  d4, d3, d0
      fabs  d3, d4
      fabs  d5, d2
      fcmp  d5, d3
      fcsel  d3, d5, d3, gt
      fcmp  d3, #0.0
      b.eq  LBB0_13
      fdiv  d5, d1, d3
      fmul  d4, d4, d5
      fmul  d2, d2, d5
      fmul  d4, d4, d4
      fmul  d2, d2, d2
      fadd  d2, d4, d2
      fsqrt  d2, d2
      fmul  d2, d3, d2
      str  d2, [x8]
      sub  x12, x12, #1
      cmp  x12, #1
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
    LBB0_8:
      ldr  d3, [x10]
      ldr  d2, [x11, x9, lsl #3]
      fadd  d4, d3, d0
      fabs  d3, d4
      fabs  d5, d2
      fcmp  d5, d3
      fcsel  d3, d5, d3, gt
      fcmp  d3, #0.0
      b.eq  LBB0_13
      sub  x13, x2, #1
      fdiv  d5, d1, d3
      fmul  d4, d4, d5
      fmul  d2, d2, d5
      fmul  d4, d4, d4
      fmul  d2, d2, d2
      fadd  d2, d4, d2
      fsqrt  d2, d2
      fmul  d2, d3, d2
      str  d2, [x8]
      mov  x14, x12
      add  x15, x10, #8
      add  x16, x8, #8
    LBB0_10:
      ldp  d3, d4, [x15, #-8]
      fadd  d4, d2, d4
      fabs  d2, d4
      fabs  d5, d3
      fcmp  d5, d2
      fcsel  d2, d5, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_13
      fdiv  d5, d1, d2
      fmul  d4, d4, d5
      fmul  d3, d3, d5
      fmul  d4, d4, d4
      fmul  d3, d3, d3
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x16], #8
      add  x15, x15, #8
      subs  x14, x14, #1
      b.ne  LBB0_10
      cmp  x2, #1
      mov  x2, x13
      b.gt  LBB0_8
      b  LBB0_6
    LBB0_13:
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

??? note "Full ASM listing: `f_add_hypot_scaled8`"
    ```asm
      .cfi_startproc
      stp  x26, x25, [sp, #-80]!
      stp  x24, x23, [sp, #16]
      stp  x22, x21, [sp, #32]
      stp  x20, x19, [sp, #48]
      stp  x29, x30, [sp, #64]
      .cfi_def_cfa_offset 80
      .cfi_offset w30, -8
      .cfi_offset w29, -16
      .cfi_offset w19, -24
      .cfi_offset w20, -32
      .cfi_offset w21, -40
      .cfi_offset w22, -48
      .cfi_offset w23, -56
      .cfi_offset w24, -64
      .cfi_offset w25, -72
      .cfi_offset w26, -80
      mov  x20, x4
      mov  x23, x3
      mov  x24, x2
      mov  x21, x1
      mov  x19, x0
      ldr  x22, [sp, #104]
    Lloh0:
      adrp  x25, _NRT_incref@GOTPAGE
    Lloh1:
      ldr  x25, [x25, _NRT_incref@GOTPAGEOFF]
      mov  x0, x4
      blr  x25
      mov  x0, x22
      blr  x25
      cmp  x24, #1
      b.lt  LBB0_19
      cmp  x23, #1
      b.lt  LBB0_19
      ldp  x9, x8, [sp, #80]
      sub  x10, x9, #8
      ldr  x11, [sp, #136]
      sub  x12, x9, #16
      sub  x13, x9, #24
      sub  x14, x9, #32
      sub  x15, x9, #40
      sub  x16, x9, #48
      sub  x17, x9, #56
      mov  x0, #22377
      movk  x0, #35604, lsl #16
      movk  x0, #48906, lsl #32
      movk  x0, #16389, lsl #48
      fmov  d0, x0
      fmov  d1, #1.00000000
      b  LBB0_4
    LBB0_3:
      cmp  x24, #1
      sub  x24, x24, #1
      b.le  LBB0_19
    LBB0_4:
      ldr  d2, [x9]
      fadd  d2, d2, d0
      fabs  d5, d2
      ldr  d3, [x10, x8, lsl #3]
      fabs  d6, d3
      fcmp  d6, d5
      ldr  d4, [x12, x8, lsl #3]
      fcsel  d5, d6, d5, gt
      fabs  d6, d4
      fcmp  d6, d5
      fcsel  d6, d6, d5, gt
      ldr  d5, [x13, x8, lsl #3]
      fabs  d7, d5
      fcmp  d7, d6
      fcsel  d7, d7, d6, gt
      ldr  d6, [x14, x8, lsl #3]
      fabs  d16, d6
      fcmp  d16, d7
      fcsel  d16, d16, d7, gt
      ldr  d7, [x15, x8, lsl #3]
      fabs  d17, d7
      fcmp  d17, d16
      fcsel  d17, d17, d16, gt
      ldr  d16, [x16, x8, lsl #3]
      fabs  d18, d16
      fcmp  d18, d17
      fcsel  d17, d18, d17, gt
      ldr  d18, [x17, x8, lsl #3]
      fabs  d19, d18
      fcmp  d19, d17
      fcsel  d17, d19, d17, gt
      fcmp  d17, #0.0
      b.eq  LBB0_20
      fdiv  d19, d1, d17
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fmul  d3, d3, d19
      fmul  d3, d3, d3
      fadd  d2, d2, d3
      fmul  d3, d4, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d5, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d7, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d18, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d3, d17, d2
      str  d3, [x11]
      cmp  x23, #1
      b.eq  LBB0_3
      ldp  d2, d4, [x9]
      fadd  d3, d3, d4
      fabs  d5, d3
      fabs  d6, d2
      fcmp  d6, d5
      ldr  d4, [x10, x8, lsl #3]
      fcsel  d5, d6, d5, gt
      fabs  d6, d4
      fcmp  d6, d5
      fcsel  d6, d6, d5, gt
      ldr  d5, [x12, x8, lsl #3]
      fabs  d7, d5
      fcmp  d7, d6
      fcsel  d7, d7, d6, gt
      ldr  d6, [x13, x8, lsl #3]
      fabs  d16, d6
      fcmp  d16, d7
      fcsel  d16, d16, d7, gt
      ldr  d7, [x14, x8, lsl #3]
      fabs  d17, d7
      fcmp  d17, d16
      fcsel  d17, d17, d16, gt
      ldr  d16, [x15, x8, lsl #3]
      fabs  d18, d16
      fcmp  d18, d17
      fcsel  d17, d18, d17, gt
      ldr  d18, [x16, x8, lsl #3]
      fabs  d19, d18
      fcmp  d19, d17
      fcsel  d17, d19, d17, gt
      fcmp  d17, #0.0
      b.eq  LBB0_20
      fdiv  d19, d1, d17
      fmul  d3, d3, d19
      fmul  d3, d3, d3
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fadd  d2, d3, d2
      fmul  d3, d4, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d5, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d7, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d18, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d2, d17, d2
      str  d2, [x11, #8]
      cmp  x23, #2
      b.eq  LBB0_3
      ldp  d3, d4, [x9, #8]
      fadd  d2, d2, d4
      fabs  d5, d2
      ldr  d4, [x9]
      fabs  d6, d3
      fcmp  d6, d5
      fcsel  d5, d6, d5, gt
      fabs  d6, d4
      fcmp  d6, d5
      fcsel  d6, d6, d5, gt
      ldr  d5, [x10, x8, lsl #3]
      fabs  d7, d5
      fcmp  d7, d6
      fcsel  d7, d7, d6, gt
      ldr  d6, [x12, x8, lsl #3]
      fabs  d16, d6
      fcmp  d16, d7
      fcsel  d16, d16, d7, gt
      ldr  d7, [x13, x8, lsl #3]
      fabs  d17, d7
      fcmp  d17, d16
      fcsel  d17, d17, d16, gt
      ldr  d16, [x14, x8, lsl #3]
      fabs  d18, d16
      fcmp  d18, d17
      fcsel  d17, d18, d17, gt
      ldr  d18, [x15, x8, lsl #3]
      fabs  d19, d18
      fcmp  d19, d17
      fcsel  d17, d19, d17, gt
      fcmp  d17, #0.0
      b.eq  LBB0_20
      fdiv  d19, d1, d17
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fmul  d3, d3, d19
      fmul  d3, d3, d3
      fadd  d2, d2, d3
      fmul  d3, d4, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d5, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d7, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d18, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d3, d17, d2
      str  d3, [x11, #16]
      cmp  x23, #3
      b.eq  LBB0_3
      ldp  d2, d4, [x9, #16]
      fadd  d3, d3, d4
      fabs  d4, d3
      fabs  d5, d2
      fcmp  d5, d4
      fcsel  d6, d5, d4, gt
      ldp  d5, d4, [x9]
      fabs  d7, d4
      fcmp  d7, d6
      fcsel  d6, d7, d6, gt
      fabs  d7, d5
      fcmp  d7, d6
      fcsel  d7, d7, d6, gt
      ldr  d6, [x10, x8, lsl #3]
      fabs  d16, d6
      fcmp  d16, d7
      fcsel  d16, d16, d7, gt
      ldr  d7, [x12, x8, lsl #3]
      fabs  d17, d7
      fcmp  d17, d16
      fcsel  d17, d17, d16, gt
      ldr  d16, [x13, x8, lsl #3]
      fabs  d18, d16
      fcmp  d18, d17
      fcsel  d17, d18, d17, gt
      ldr  d18, [x14, x8, lsl #3]
      fabs  d19, d18
      fcmp  d19, d17
      fcsel  d17, d19, d17, gt
      fcmp  d17, #0.0
      b.eq  LBB0_20
      fdiv  d19, d1, d17
      fmul  d3, d3, d19
      fmul  d3, d3, d3
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fadd  d2, d3, d2
      fmul  d3, d4, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d5, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d7, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d18, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d2, d17, d2
      str  d2, [x11, #24]
      cmp  x23, #4
      b.eq  LBB0_3
      ldp  d3, d4, [x9, #24]
      fadd  d2, d2, d4
      fabs  d5, d2
      ldr  d4, [x9, #16]
      fabs  d6, d3
      fcmp  d6, d5
      fcsel  d5, d6, d5, gt
      fabs  d6, d4
      fcmp  d6, d5
      fcsel  d7, d6, d5, gt
      ldp  d6, d5, [x9]
      fabs  d16, d5
      fcmp  d16, d7
      fcsel  d7, d16, d7, gt
      fabs  d16, d6
      fcmp  d16, d7
      fcsel  d16, d16, d7, gt
      ldr  d7, [x10, x8, lsl #3]
      fabs  d17, d7
      fcmp  d17, d16
      fcsel  d17, d17, d16, gt
      ldr  d16, [x12, x8, lsl #3]
      fabs  d18, d16
      fcmp  d18, d17
      fcsel  d17, d18, d17, gt
      ldr  d18, [x13, x8, lsl #3]
      fabs  d19, d18
      fcmp  d19, d17
      fcsel  d17, d19, d17, gt
      fcmp  d17, #0.0
      b.eq  LBB0_20
      fdiv  d19, d1, d17
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fmul  d3, d3, d19
      fmul  d3, d3, d3
      fadd  d2, d2, d3
      fmul  d3, d4, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d5, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d7, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d18, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d3, d17, d2
      str  d3, [x11, #32]
      cmp  x23, #5
      b.eq  LBB0_3
      ldp  d2, d4, [x9, #32]
      fadd  d3, d3, d4
      fabs  d4, d3
      fabs  d5, d2
      fcmp  d5, d4
      fcsel  d6, d5, d4, gt
      ldp  d5, d4, [x9, #16]
      fabs  d7, d4
      fcmp  d7, d6
      fcsel  d6, d7, d6, gt
      fabs  d7, d5
      fcmp  d7, d6
      fcsel  d16, d7, d6, gt
      ldp  d7, d6, [x9]
      fabs  d17, d6
      fcmp  d17, d16
      fcsel  d16, d17, d16, gt
      fabs  d17, d7
      fcmp  d17, d16
      fcsel  d17, d17, d16, gt
      ldr  d16, [x10, x8, lsl #3]
      fabs  d18, d16
      fcmp  d18, d17
      fcsel  d17, d18, d17, gt
      ldr  d18, [x12, x8, lsl #3]
      fabs  d19, d18
      fcmp  d19, d17
      fcsel  d17, d19, d17, gt
      fcmp  d17, #0.0
      b.eq  LBB0_20
      fdiv  d19, d1, d17
      fmul  d3, d3, d19
      fmul  d3, d3, d3
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fadd  d2, d3, d2
      fmul  d3, d4, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d5, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d7, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d18, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d3, d17, d2
      str  d3, [x11, #40]
      cmp  x23, #6
      b.eq  LBB0_3
      sub  x2, x9, #8
      mov  w1, #6
      mov  x0, x2
    LBB0_17:
      ldp  d2, d4, [x2, #48]
      fadd  d3, d3, d4
      fabs  d4, d3
      fabs  d5, d2
      fcmp  d5, d4
      fcsel  d6, d5, d4, gt
      ldp  d5, d4, [x2, #32]
      fabs  d7, d4
      fcmp  d7, d6
      fcsel  d6, d7, d6, gt
      fabs  d7, d5
      fcmp  d7, d6
      fcsel  d16, d7, d6, gt
      ldp  d7, d6, [x2, #16]
      fabs  d17, d6
      fcmp  d17, d16
      fcsel  d17, d17, d16, gt
      fabs  d18, d7
      fcmp  d18, d17
      ldr  d16, [x0, #8]!
      fcsel  d17, d18, d17, gt
      fabs  d18, d16
      fcmp  d18, d17
      fcsel  d17, d18, d17, gt
      cmp  x1, #7
      csel  x3, x8, xzr, lo
      ldr  d18, [x2, x3, lsl #3]
      fabs  d19, d18
      fcmp  d19, d17
      fcsel  d17, d19, d17, gt
      fcmp  d17, #0.0
      b.eq  LBB0_20
      fdiv  d19, d1, d17
      fmul  d3, d3, d19
      fmul  d3, d3, d3
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fadd  d2, d3, d2
      fmul  d3, d4, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d5, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d7, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d18, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d3, d17, d2
      str  d3, [x11, x1, lsl #3]
      add  x1, x1, #1
      mov  x2, x0
      cmp  x23, x1
      b.ne  LBB0_17
      b  LBB0_3
    LBB0_19:
    Lloh2:
      adrp  x21, _NRT_decref@GOTPAGE
    Lloh3:
      ldr  x21, [x21, _NRT_decref@GOTPAGEOFF]
      mov  x0, x22
      blr  x21
      mov  x0, x20
      blr  x21
      mov  w0, #0
      str  xzr, [x19]
      ldp  x29, x30, [sp, #64]
      ldp  x20, x19, [sp, #48]
      ldp  x22, x21, [sp, #32]
      ldp  x24, x23, [sp, #16]
      ldp  x26, x25, [sp], #80
      ret
    LBB0_20:
    Lloh4:
      adrp  x8, _.const.picklebuf.<addr>@GOTPAGE
    Lloh5:
      ldr  x8, [x8, _.const.picklebuf.<addr>@GOTPAGEOFF]
      str  x8, [x21]
      mov  w0, #1
      ldp  x29, x30, [sp, #64]
      ldp  x20, x19, [sp, #48]
      ldp  x22, x21, [sp, #32]
      ldp  x24, x23, [sp, #16]
      ldp  x26, x25, [sp], #80
      ret
      .loh AdrpLdrGot  Lloh0, Lloh1
      .loh AdrpLdrGot  Lloh2, Lloh3
      .loh AdrpLdrGot  Lloh4, Lloh5
      .cfi_endproc
    ```
<!-- END generated: kernel-asm-hypot-xarg-structure -->

## Discussion

**The subtraction isolates six extra coordinates' worth of the scaled-hypot algorithm, and the
÷6 therefore prices one coordinate.**

1. *Intended work, and nothing else*: the added lines decompose per extra coordinate into the
   max-scan step (`fabs` + `fcmp` + `fcsel`, with an `ldp`/`ldr` load per coordinate pair) and
   the accumulation step (`fmul` scale, `fmul` square, `fadd` accumulate) — six of each, matching
   the six extra coordinates exactly. The shared skeleton (reciprocal `fdiv`, final `fsqrt`,
   rescale `fmul`, store, loop control) appears once on both sides, unchanged. The one addition
   that is *not* floating-point work is an integer `cmp`/`csel` pair feeding one load — index
   wraparound handling for the deepest negative array offset. It runs on the integer side,
   overlapping the floating-point chain rather than extending it, so it does not contaminate the
   measured latency.
2. *In the dependency chain*: both the max-scan (`fcsel` chain into the reciprocal) and the
   accumulation (`fadd` chain into the `fsqrt`) serialize per coordinate, and the result feeds
   the next iteration's first coordinate — more coordinates means a proportionally longer chain,
   which is precisely what a per-coordinate latency slope should measure.
3. *Loop-structure symmetry*: neither kernel unrolls (the bodies are large enough that LLVM
   leaves them alone). Each kernel compiles to two variants of its loop with an identical
   floating-point sequence, differing only in address computation (index-wraparound handling);
   the diff shows the best-matching pair of variants.
