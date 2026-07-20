# DIST_XARG

The `DIST_XARG` cost is the per-extra-coordinate slope of the overflow-safe scaled `dist`
algorithm: the latency difference between its 8-coordinate and 2-coordinate forms — kernels
`f_add_dist8` and `f_add_dist2` — divided by the 6 extra coordinates. Exemplar of the same
construction as [HYPOT_XARG](hypot_xarg.md): the two sides are the same algorithm at two sizes,
so the diff is expected to be large — what must hold is that every added line belongs to the six
extra coordinates, and nothing shared changed shape. Why the slope is measured on a hand-rolled overflow-safe port is covered in the [benchmark design rationale](../analysis_methodology.md#16-benchmark-design-rationale).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-dist-xarg-diff -->
```diff
--- f_add_dist2
+++ f_add_dist8
  .L0:
- ldr  %d0, [%x0]
- ldr  %d1, [%x1, %x2, lsl #3]
- ldr  %d2, [%x3, %x2, lsl #3]
- fadd  %d3, %d0, %d4
- fabd  %d0, %d3, %d1
- fabd  %d5, %d1, %d2
- fcmp  %d5, %d0
- fcsel  %d0, %d5, %d0, gt
+ cmp  %x0, #1
+ sub  %x0, %x0, #1
+ b.le  .L1
+ .L2:
+ ldr  %d0, [%x1]
+ ldr  %d1, [%x2, %x3, lsl #3]
+ ldr  %d2, [%x4, %x3, lsl #3]
+ ldr  %d3, [%x5, %x3, lsl #3]
+ ldr  %d4, [%x6, %x3, lsl #3]
+ ldr  %d5, [%x7, %x3, lsl #3]
+ ldr  %d6, [%x8, %x3, lsl #3]
+ ldr  %d7, [%x9, %x3, lsl #3]
+ ldr  %d8, [%x10, %x3, lsl #3]
+ fadd  %d9, %d0, %d10
+ fabd  %d0, %d9, %d1
+ fabd  %d11, %d1, %d2
+ fcmp  %d11, %d0
+ fcsel  %d0, %d11, %d0, gt
+ fabd  %d11, %d2, %d3
+ fcmp  %d11, %d0
+ fcsel  %d0, %d11, %d0, gt
+ fabd  %d11, %d3, %d4
+ fcmp  %d11, %d0
+ fcsel  %d0, %d11, %d0, gt
+ fabd  %d11, %d4, %d5
+ fcmp  %d11, %d0
+ fcsel  %d0, %d11, %d0, gt
+ fabd  %d11, %d5, %d6
+ fcmp  %d11, %d0
+ fcsel  %d0, %d11, %d0, gt
+ fabd  %d11, %d6, %d7
+ fcmp  %d11, %d0
+ fcsel  %d0, %d11, %d0, gt
+ fabd  %d11, %d7, %d8
+ fcmp  %d11, %d0
+ fcsel  %d0, %d11, %d0, gt
  fcmp  %d0, #0.0
- b.eq  .L1
- fsub  %d3, %d3, %d1
+ b.eq  .L3
+ fsub  %d9, %d9, %d1
  fsub  %d1, %d1, %d2
- fdiv  %d2, %d6, %d0
- fmul  %d3, %d3, %d2
- fmul  %d1, %d1, %d2
- fmul  %d2, %d3, %d3
+ fsub  %d2, %d2, %d3
+ fsub  %d3, %d3, %d4
+ fsub  %d4, %d4, %d5
+ fsub  %d5, %d5, %d6
+ fsub  %d6, %d6, %d7
+ fsub  %d7, %d7, %d8
+ fdiv  %d8, %d12, %d0
+ fmul  %d9, %d9, %d8
+ fmul  %d9, %d9, %d9
+ fmul  %d1, %d1, %d8
  fmul  %d1, %d1, %d1
+ fadd  %d1, %d9, %d1
+ fmul  %d2, %d2, %d8
+ fmul  %d2, %d2, %d2
+ fadd  %d1, %d2, %d1
+ fmul  %d2, %d3, %d8
+ fmul  %d2, %d2, %d2
+ fadd  %d1, %d2, %d1
+ fmul  %d2, %d4, %d8
+ fmul  %d2, %d2, %d2
+ fadd  %d1, %d2, %d1
+ fmul  %d2, %d5, %d8
+ fmul  %d2, %d2, %d2
+ fadd  %d1, %d2, %d1
+ fmul  %d2, %d6, %d8
+ fmul  %d2, %d2, %d2
+ fadd  %d1, %d2, %d1
+ fmul  %d2, %d7, %d8
+ fmul  %d2, %d2, %d2
  fadd  %d1, %d2, %d1
  fsqrt  %d1, %d1
  fmul  %d0, %d0, %d1
- str  %d0, [%x4]
- sub  %x5, %x5, #1
- cmp  %x5, #1
- b.gt  .L0
+ str  %d0, [%x11]
+ cmp  %x12, #1
+ b.eq  .L0
```
<!-- END generated: kernel-asm-dist-xarg-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-dist-xarg-structure -->
- `f_add_dist2` -- 3 innermost loop(s): 25 instructions, 60 instructions, 24 instructions
- `f_add_dist8` -- 2 innermost loop(s): 76 instructions, 86 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the kernels'
amount of work -- see the discussion below.

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

??? note "Full ASM listing: `f_add_dist8`"
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
      b.lt  LBB0_17
      cmp  x23, #1
      b.lt  LBB0_17
      ldp  x9, x8, [sp, #80]
      sub  x10, x9, #8
      sub  x11, x9, #16
      sub  x12, x9, #24
      sub  x13, x9, #32
      ldr  x14, [sp, #136]
      sub  x15, x9, #40
      sub  x16, x9, #48
      sub  x17, x9, #56
      sub  x0, x9, #64
      add  x1, x14, #40
      sub  x2, x23, #5
      mov  x3, #22377
      movk  x3, #35604, lsl #16
      movk  x3, #48906, lsl #32
      movk  x3, #16389, lsl #48
      fmov  d0, x3
      fmov  d1, #1.00000000
      b  LBB0_4
    LBB0_3:
      cmp  x24, #1
      sub  x24, x24, #1
      b.le  LBB0_17
    LBB0_4:
      ldr  d2, [x9]
      ldr  d3, [x10, x8, lsl #3]
      ldr  d4, [x11, x8, lsl #3]
      ldr  d5, [x12, x8, lsl #3]
      ldr  d6, [x13, x8, lsl #3]
      ldr  d7, [x15, x8, lsl #3]
      ldr  d16, [x16, x8, lsl #3]
      ldr  d17, [x17, x8, lsl #3]
      ldr  d18, [x0, x8, lsl #3]
      fadd  d19, d2, d0
      fabd  d2, d19, d3
      fabd  d20, d3, d4
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d4, d5
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d5, d6
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d6, d7
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d7, d16
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d16, d17
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d17, d18
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_18
      fsub  d19, d19, d3
      fsub  d3, d3, d4
      fsub  d4, d4, d5
      fsub  d5, d5, d6
      fsub  d6, d6, d7
      fsub  d7, d7, d16
      fsub  d16, d16, d17
      fsub  d17, d17, d18
      fdiv  d18, d1, d2
      fmul  d19, d19, d18
      fmul  d19, d19, d19
      fmul  d3, d3, d18
      fmul  d3, d3, d3
      fadd  d3, d19, d3
      fmul  d4, d4, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d5, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d6, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d7, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d16, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d17, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x14]
      cmp  x23, #1
      b.eq  LBB0_3
      ldp  d3, d19, [x9]
      ldr  d4, [x10, x8, lsl #3]
      ldr  d5, [x11, x8, lsl #3]
      ldr  d6, [x12, x8, lsl #3]
      ldr  d7, [x13, x8, lsl #3]
      ldr  d16, [x15, x8, lsl #3]
      ldr  d17, [x16, x8, lsl #3]
      ldr  d18, [x17, x8, lsl #3]
      fadd  d19, d2, d19
      fabd  d2, d19, d3
      fabd  d20, d3, d4
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d4, d5
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d5, d6
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d6, d7
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d7, d16
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d16, d17
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d17, d18
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_18
      fsub  d19, d19, d3
      fsub  d3, d3, d4
      fsub  d4, d4, d5
      fsub  d5, d5, d6
      fsub  d6, d6, d7
      fsub  d7, d7, d16
      fsub  d16, d16, d17
      fsub  d17, d17, d18
      fdiv  d18, d1, d2
      fmul  d19, d19, d18
      fmul  d19, d19, d19
      fmul  d3, d3, d18
      fmul  d3, d3, d3
      fadd  d3, d19, d3
      fmul  d4, d4, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d5, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d6, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d7, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d16, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d17, d18
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x14, #8]
      cmp  x23, #2
      b.eq  LBB0_3
      ldp  d18, d7, [x9, #8]
      ldr  d3, [x10, x8, lsl #3]
      ldr  d4, [x11, x8, lsl #3]
      ldr  d5, [x12, x8, lsl #3]
      ldr  d6, [x13, x8, lsl #3]
      fadd  d17, d2, d7
      ldr  d7, [x15, x8, lsl #3]
      ldr  d16, [x16, x8, lsl #3]
      ldr  d19, [x9]
      fabd  d2, d17, d18
      fabd  d20, d18, d19
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d19, d3
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d3, d4
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d4, d5
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d5, d6
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d6, d7
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d7, d16
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_18
      fsub  d17, d17, d18
      fsub  d18, d18, d19
      fsub  d19, d19, d3
      fsub  d3, d3, d4
      fsub  d4, d4, d5
      fsub  d5, d5, d6
      fsub  d6, d6, d7
      fsub  d7, d7, d16
      fdiv  d16, d1, d2
      fmul  d17, d17, d16
      fmul  d17, d17, d17
      fmul  d18, d18, d16
      fmul  d18, d18, d18
      fadd  d17, d17, d18
      fmul  d18, d19, d16
      fmul  d18, d18, d18
      fadd  d17, d18, d17
      fmul  d3, d3, d16
      fmul  d3, d3, d3
      fadd  d3, d3, d17
      fmul  d4, d4, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d5, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d6, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d7, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x14, #16]
      cmp  x23, #3
      b.eq  LBB0_3
      ldp  d3, d7, [x9, #16]
      ldr  d4, [x10, x8, lsl #3]
      ldr  d5, [x11, x8, lsl #3]
      ldr  d6, [x12, x8, lsl #3]
      fadd  d17, d2, d7
      ldr  d7, [x13, x8, lsl #3]
      ldr  d16, [x15, x8, lsl #3]
      ldp  d19, d18, [x9]
      fabd  d2, d17, d3
      fabd  d20, d3, d18
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d18, d19
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d19, d4
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d4, d5
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d5, d6
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d6, d7
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fabd  d20, d7, d16
      fcmp  d20, d2
      fcsel  d2, d20, d2, gt
      fcmp  d2, #0.0
      b.eq  LBB0_18
      fsub  d17, d17, d3
      fsub  d3, d3, d18
      fsub  d18, d18, d19
      fsub  d19, d19, d4
      fsub  d4, d4, d5
      fsub  d5, d5, d6
      fsub  d6, d6, d7
      fsub  d7, d7, d16
      fdiv  d16, d1, d2
      fmul  d17, d17, d16
      fmul  d17, d17, d17
      fmul  d3, d3, d16
      fmul  d3, d3, d3
      fadd  d3, d17, d3
      fmul  d17, d18, d16
      fmul  d17, d17, d17
      fadd  d3, d17, d3
      fmul  d17, d19, d16
      fmul  d17, d17, d17
      fadd  d3, d17, d3
      fmul  d4, d4, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d5, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d6, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fmul  d4, d7, d16
      fmul  d4, d4, d4
      fadd  d3, d4, d3
      fsqrt  d3, d3
      fmul  d2, d2, d3
      str  d2, [x14, #24]
      cmp  x23, #4
      b.eq  LBB0_3
      ldp  d16, d3, [x9, #24]
      fadd  d2, d2, d3
      ldr  d3, [x10, x8, lsl #3]
      ldr  d4, [x11, x8, lsl #3]
      ldp  d18, d17, [x9, #8]
      ldr  d6, [x12, x8, lsl #3]
      ldr  d7, [x13, x8, lsl #3]
      ldr  d19, [x9]
      fabd  d5, d2, d16
      fabd  d20, d16, d17
      fcmp  d20, d5
      fcsel  d5, d20, d5, gt
      fabd  d20, d17, d18
      fcmp  d20, d5
      fcsel  d5, d20, d5, gt
      fabd  d20, d18, d19
      fcmp  d20, d5
      fcsel  d5, d20, d5, gt
      fabd  d20, d19, d3
      fcmp  d20, d5
      fcsel  d5, d20, d5, gt
      fabd  d20, d3, d4
      fcmp  d20, d5
      fcsel  d5, d20, d5, gt
      fabd  d20, d4, d6
      fcmp  d20, d5
      fcsel  d5, d20, d5, gt
      fabd  d20, d6, d7
      fcmp  d20, d5
      fcsel  d5, d20, d5, gt
      fcmp  d5, #0.0
      b.eq  LBB0_18
      fsub  d2, d2, d16
      fsub  d16, d16, d17
      fsub  d17, d17, d18
      fsub  d18, d18, d19
      fsub  d19, d19, d3
      fsub  d3, d3, d4
      fsub  d4, d4, d6
      fsub  d6, d6, d7
      fdiv  d7, d1, d5
      fmul  d2, d2, d7
      fmul  d2, d2, d2
      fmul  d16, d16, d7
      fmul  d16, d16, d16
      fadd  d2, d2, d16
      fmul  d16, d17, d7
      fmul  d16, d16, d16
      fadd  d2, d16, d2
      fmul  d16, d18, d7
      fmul  d16, d16, d16
      fadd  d2, d16, d2
      fmul  d16, d19, d7
      fmul  d16, d16, d16
      fadd  d2, d16, d2
      fmul  d3, d3, d7
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d4, d7
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d6, d7
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d3, d5, d2
      str  d3, [x14, #32]
      cmp  x23, #5
      b.eq  LBB0_3
      mov  x3, #0
      mov  w4, #40
    LBB0_15:
      add  x5, x3, #5
      add  x6, x9, x4
      ldp  d2, d4, [x6, #-8]
      fadd  d7, d3, d4
      ldp  d4, d3, [x6, #-24]
      ldp  d6, d5, [x6, #-40]
      cmp  x5, #6
      csel  x6, x8, xzr, lo
      add  x6, x9, x6, lsl #3
      lsl  x7, x3, #3
      add  x6, x6, x7
      ldur  d16, [x6, #-8]
      cmp  x5, #7
      csel  x6, x8, xzr, lo
      add  x6, x9, x6, lsl #3
      add  x6, x6, x7
      ldur  d17, [x6, #-16]
      cmp  x5, #8
      csel  x5, x8, xzr, lo
      add  x5, x9, x5, lsl #3
      add  x5, x5, x7
      ldur  d19, [x5, #-24]
      fabd  d18, d7, d2
      fabd  d20, d2, d3
      fcmp  d20, d18
      fcsel  d18, d20, d18, gt
      fabd  d20, d3, d4
      fcmp  d20, d18
      fcsel  d18, d20, d18, gt
      fabd  d20, d4, d5
      fcmp  d20, d18
      fcsel  d18, d20, d18, gt
      fabd  d20, d5, d6
      fcmp  d20, d18
      fcsel  d18, d20, d18, gt
      fabd  d20, d6, d16
      fcmp  d20, d18
      fcsel  d18, d20, d18, gt
      fabd  d20, d16, d17
      fcmp  d20, d18
      fcsel  d18, d20, d18, gt
      fabd  d20, d17, d19
      fcmp  d20, d18
      fcsel  d18, d20, d18, gt
      fcmp  d18, #0.0
      b.eq  LBB0_18
      fsub  d7, d7, d2
      fsub  d2, d2, d3
      fsub  d3, d3, d4
      fsub  d4, d4, d5
      fsub  d5, d5, d6
      fsub  d6, d6, d16
      fsub  d16, d16, d17
      fsub  d17, d17, d19
      fdiv  d19, d1, d18
      fmul  d7, d7, d19
      fmul  d7, d7, d7
      fmul  d2, d2, d19
      fmul  d2, d2, d2
      fadd  d2, d7, d2
      fmul  d3, d3, d19
      fmul  d3, d3, d3
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
      fmul  d3, d16, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fmul  d3, d17, d19
      fmul  d3, d3, d3
      fadd  d2, d3, d2
      fsqrt  d2, d2
      fmul  d3, d18, d2
      str  d3, [x1, x3, lsl #3]
      add  x3, x3, #1
      add  x4, x4, #8
      cmp  x2, x3
      b.ne  LBB0_15
      b  LBB0_3
    LBB0_17:
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
    LBB0_18:
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
<!-- END generated: kernel-asm-dist-xarg-structure -->

## Discussion

**The subtraction isolates six extra coordinates' worth of the scaled-distance algorithm, and
the ÷6 therefore prices one coordinate.**

1. *Intended work, and nothing else*: per extra coordinate, the additions decompose into one
   load, one `fabd` (the delta and its absolute value, fused), the max-scan step
   (`fcmp` + `fcsel`), and the accumulation step (`fmul` scale, `fmul` square, `fadd`
   accumulate) — six of each. The shared skeleton (zero-guard, reciprocal `fdiv`, final
   `fsqrt`, rescale, store, loop control) appears once on both sides.
2. *In the dependency chain*: the max-scan chain and the accumulation chain both lengthen
   proportionally with the coordinate count, and the result feeds the next iteration's first
   delta — which is precisely what a per-coordinate latency slope should measure.
3. *Loop-structure symmetry*: neither kernel unrolls; both carry the same zero-guard, whose
   rotated variants account for the multiple regions in the inventory. The diff shows the
   best-matching region pair.
