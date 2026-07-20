# CBRT

The `CBRT` cost is the latency difference between a kernel chaining `np.cbrt(tmp + x[i])` and
one chaining only `tmp + x[i]` — kernels `f_add_cbrt` and `f_add`. A libm call — with extra
handling: numba implements `np.cbrt` with its own NaN check and negative-argument handling
around the `cbrt` call, and that wrapper code is part of what the weight measures.

What Python code counts into `CBRT` is described in
[FLOP types](../flop_types.md#flop-cbrt).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-cbrt-diff -->
```diff
--- f_add
+++ f_add_cbrt
  .L0:
- ldr  %d0, [%x0], #8
- fadd  %d1, %d1, %d0
- str  %d1, [%x1], #8
- subs  %x2, %x2, #1
- b.ne  .L0
+ subs  %x0, %x0, #1
+ b.le  .L1
+ .L2:
+ mov  %x1, %x2
+ mov  %x3, %x4
+ mov  %x5, %x6
+ mov.16b  %v0, %v1
+ b  .L3
+ .L4:
+ blr  %x7
+ .L5:
+ str  %d0, [%x5], #8
+ subs  %x1, %x1, #1
+ b.eq  .L0
+ .L3:
+ ldr  %d2, [%x3], #8
+ fadd  %d0, %d0, %d2
+ fcmp  %d0, %d0
+ b.vs  .L6
+ fcmp  %d0, #0.0
+ b.ge  .L4
+ fneg  %d0, %d0
+ blr  %x7
+ fneg  %d0, %d0
+ b  .L5
```
<!-- END generated: kernel-asm-cbrt-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-cbrt-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_cbrt` -- 1 innermost loop(s): 26 instructions

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

??? note "Full ASM listing: `f_add_cbrt`"
    ```asm
      .cfi_startproc
      stp  d9, d8, [sp, #-112]!
      stp  x28, x27, [sp, #16]
      stp  x26, x25, [sp, #32]
      stp  x24, x23, [sp, #48]
      stp  x22, x21, [sp, #64]
      stp  x20, x19, [sp, #80]
      stp  x29, x30, [sp, #96]
      .cfi_def_cfa_offset 112
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
      .cfi_offset w27, -88
      .cfi_offset w28, -96
      .cfi_offset b8, -104
      .cfi_offset b9, -112
      mov  x19, x0
      cmp  x2, #1
      b.lt  LBB0_11
      mov  x20, x3
      cmp  x3, #1
      b.lt  LBB0_11
      mov  x21, x2
      ldr  x22, [sp, #168]
      ldr  x23, [sp, #112]
      mov  x8, #22377
      movk  x8, #35604, lsl #16
      movk  x8, #48906, lsl #32
      movk  x8, #16389, lsl #48
      fmov  d8, x8
    Lloh0:
      adrp  x24, _cbrt@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _cbrt@GOTPAGEOFF]
      b  LBB0_4
    LBB0_3:
      subs  x21, x21, #1
      b.le  LBB0_11
    LBB0_4:
      mov  x25, x20
      mov  x26, x23
      mov  x27, x22
      mov.16b  v0, v8
      b  LBB0_7
    LBB0_5:
      blr  x24
    LBB0_6:
      str  d0, [x27], #8
      subs  x25, x25, #1
      b.eq  LBB0_3
    LBB0_7:
      ldr  d1, [x26], #8
      fadd  d0, d0, d1
      fcmp  d0, d0
      b.vs  LBB0_10
      fcmp  d0, #0.0
      b.ge  LBB0_5
      fneg  d0, d0
      blr  x24
      fneg  d0, d0
      b  LBB0_6
    LBB0_10:
      mov  x8, #9221120237041090560
      fmov  d0, x8
      b  LBB0_6
    LBB0_11:
      str  xzr, [x19]
      mov  w0, #0
      ldp  x29, x30, [sp, #96]
      ldp  x20, x19, [sp, #80]
      ldp  x22, x21, [sp, #64]
      ldp  x24, x23, [sp, #48]
      ldp  x26, x25, [sp, #32]
      ldp  x28, x27, [sp, #16]
      ldp  d9, d8, [sp], #112
      ret
      .loh AdrpLdrGot  Lloh0, Lloh1
      .cfi_endproc
    ```
<!-- END generated: kernel-asm-cbrt-structure -->

## Discussion

**The subtraction isolates one `cbrt` call plus numba's NaN/sign wrapper around it.**

1. *What the diff shows*: the loop compiled to a *rotated* form — its cycle closes through
   forward branches and fallthrough rather than one backward branch, so it appears as a single
   merged region and the diff aligns almost nothing with `f_add`. Reading the `+` side as a
   whole: load and `fadd` as usual, then a NaN check (`fcmp %d0, %d0` + `b.vs`), then either a
   direct `cbrt` call for non-negative arguments or a `fneg` → `cbrt` → `fneg` sequence for
   negative ones (`cbrt(-x) = -cbrt(x)`). The region also carries the outer loop's reset code,
   entangled by the rotation. The priced work is therefore call + compare/branch wrapper — a
   faithful account of what `np.cbrt` costs under numba, slightly more than a bare libm call.
2. *In the dependency chain*: the NaN check, the sign branches and the call all depend on the
   accumulator and feed its next value, so the whole wrapper sits in the serialized chain. The
   kernel's mixed-sign input range exercises both sign paths.
3. *Loop-structure symmetry*: `f_add` unrolls 8×; the branchy cbrt loop cannot unroll. As on
   the [SQRT page](sqrt.md), both sides remain latency-bound, so the subtraction holds.
