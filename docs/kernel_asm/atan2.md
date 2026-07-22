# ATAN2

The `ATAN2` cost is the latency difference between a kernel chaining
`atan2(tmp + x[i], x[i])` and one chaining only `tmp + x[i]` — kernels `f_add_atan2` and
`f_add`. A libm call with two arguments: the chained value and the freshly loaded element. The kernel's input range keeps most magnitudes above 1, matching `atan`'s general-case regime; the cost is flat from there through huge arguments.

What Python code counts into `ATAN2` is described in
[FLOP types](../flop_types.md#flop-atan2).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-atan2-diff -->
```diff
--- f_add
+++ f_add_atan2
  .L0:
- ldr  %d0, [%x0], #8
+ ldur  %d0, [%x0, #-8]
  fadd  %d1, %d1, %d0
- str  %d1, [%x1], #8
- subs  %x2, %x2, #1
+ blr  %x1
+ stur  %d1, [%x2, #-8]
+ add  %x3, %x3, #2
+ ldr  %d0, [%x0], #16
+ fadd  %d1, %d1, %d0
+ blr  %x1
+ str  %d1, [%x2], #16
+ cmp  %x4, %x3
  b.ne  .L0
```
<!-- END generated: kernel-asm-atan2-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-atan2-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_atan2` -- 2 innermost loop(s): 14 instructions, 12 instructions

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

??? note "Full ASM listing: `f_add_atan2`"
    ```asm
      stp  d9, d8, [sp, #-112]!
      stp  x28, x27, [sp, #16]
      stp  x26, x25, [sp, #32]
      stp  x24, x23, [sp, #48]
      stp  x22, x21, [sp, #64]
      stp  x20, x19, [sp, #80]
      stp  x29, x30, [sp, #96]
      mov  x19, x0
      cmp  x2, #1
      b.lt  LBB0_10
      mov  x20, x3
      cmp  x3, #1
      b.lt  LBB0_10
      mov  x21, x2
      ldr  x22, [sp, #168]
      ldr  x23, [sp, #112]
      and  x24, x20, #0x7ffffffffffffffe
      mov  x8, #22377
      movk  x8, #35604, lsl #16
      movk  x8, #48906, lsl #32
      movk  x8, #16389, lsl #48
      fmov  d8, x8
    Lloh0:
      adrp  x25, _atan2@GOTPAGE
    Lloh1:
      ldr  x25, [x25, _atan2@GOTPAGEOFF]
      b  LBB0_6
    LBB0_3:
      mov  x26, #0
      mov.16b  v0, v8
    LBB0_4:
      ldr  d1, [x23, x26, lsl #3]
      fadd  d0, d0, d1
      blr  x25
      str  d0, [x22, x26, lsl #3]
    LBB0_5:
      subs  x21, x21, #1
      b.le  LBB0_10
    LBB0_6:
      cmp  x20, #1
      b.eq  LBB0_3
      mov  x26, #0
      add  x27, x22, #8
      add  x28, x23, #8
      mov.16b  v0, v8
    LBB0_8:
      ldur  d1, [x28, #-8]
      fadd  d0, d0, d1
      blr  x25
      stur  d0, [x27, #-8]
      add  x26, x26, #2
      ldr  d1, [x28], #16
      fadd  d0, d0, d1
      blr  x25
      str  d0, [x27], #16
      cmp  x24, x26
      b.ne  LBB0_8
      tbnz  w20, #0, LBB0_4
      b  LBB0_5
    LBB0_10:
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
    ```
<!-- END generated: kernel-asm-atan2-structure -->

## Discussion

**The subtraction isolates exactly one call to libm's `atan2` per element.**

1. *Intended call, and nothing else*: the structural addition is one `blr` per element — the
   `atan2` call through a preloaded call-target register. The remaining `-`/`+` pairs are
   addressing differences between the two unrolling shapes (see point 3), not extra work.
2. *In the dependency chain*: `fadd` produces the first argument, the call's return value feeds
   the next iteration's `fadd`; the second argument is the freshly loaded element, off the
   chain.
3. *Loop-structure symmetry*: **not symmetric** — `f_add` unrolls 8×, and `f_add_atan2`
   compiles 2×-unrolled (one call per element either way). As on the [SQRT page](sqrt.md), both
   sides stay latency-bound through the accumulator, so the subtraction holds.
