# FMOD

The `FMOD` cost is the latency difference between a kernel chaining `np.fmod(tmp + x[i])` and
one chaining only `tmp + x[i]` — kernels `f_add_fmod` and `f_add`. Like most libm-backed functions,
`np.fmod` compiles to a call into the math library. The kernel's strictly positive divisor range avoids the `fmod(x, 0)` domain error.

What Python code counts into `FMOD` is described in
[FLOP types](../flop_types.md#flop-fmod).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-fmod-diff -->
```diff
--- f_add
+++ f_add_fmod
  .L0:
  ldr  %d0, [%x0], #8
  fadd  %d1, %d1, %d0
- str  %d1, [%x1], #8
- subs  %x2, %x2, #1
+ blr  %x1
+ str  %d1, [%x2], #8
+ subs  %x3, %x3, #1
  b.ne  .L0
```
<!-- END generated: kernel-asm-fmod-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-fmod-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_fmod` -- 2 innermost loop(s): 17 instructions, 7 instructions

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

??? note "Full ASM listing: `f_add_fmod`"
    ```asm
      sub  sp, sp, #144
      stp  d9, d8, [sp, #32]
      stp  x28, x27, [sp, #48]
      stp  x26, x25, [sp, #64]
      stp  x24, x23, [sp, #80]
      stp  x22, x21, [sp, #96]
      stp  x20, x19, [sp, #112]
      stp  x29, x30, [sp, #128]
      str  x0, [sp, #16]
      cmp  x2, #1
      b.lt  LBB0_12
      subs  x21, x3, #1
      b.lt  LBB0_12
      mov  x20, x2
      ldr  x22, [sp, #200]
      ldr  x23, [sp, #144]
      mov  x8, #-6148914691236517206
      movk  x8, #43691
      umulh  x8, x21, x8
      lsr  x8, x8, #1
      add  x8, x8, x8, lsl #1
      sub  x8, x21, x8
      add  x10, x8, #1
      add  x9, x8, #1
      str  x9, [sp, #24]
      cmp  x10, #3
      csinc  x25, xzr, x8, eq
      sub  x26, x25, x3
      mov  x8, #22377
      movk  x8, #35604, lsl #16
      movk  x8, #48906, lsl #32
      movk  x8, #16389, lsl #48
      fmov  d8, x8
    Lloh0:
      adrp  x27, _fmod@GOTPAGE
    Lloh1:
      ldr  x27, [x27, _fmod@GOTPAGEOFF]
      b  LBB0_4
    LBB0_3:
      subs  x20, x20, #1
      b.le  LBB0_12
    LBB0_4:
      cmp  x21, #2
      b.hs  LBB0_6
      mov  x8, #0
      mov.16b  v0, v8
      b  LBB0_10
    LBB0_6:
      mov  x28, #0
      add  x19, x23, #16
      add  x24, x22, #8
      mov.16b  v0, v8
    LBB0_7:
      ldur  d1, [x19, #-16]
      fadd  d0, d0, d1
      blr  x27
      stur  d0, [x24, #-8]
      ldur  d1, [x19, #-8]
      fadd  d0, d0, d1
      blr  x27
      str  d0, [x24]
      ldr  d1, [x19], #24
      fadd  d0, d0, d1
      blr  x27
      str  d0, [x24, #8]
      add  x24, x24, #24
      sub  x28, x28, #3
      cmp  x26, x28
      b.ne  LBB0_7
      ldr  x8, [sp, #24]
      cmp  x8, #3
      b.eq  LBB0_3
      neg  x8, x28
    LBB0_10:
      lsl  x8, x8, #3
      add  x19, x22, x8
      add  x24, x23, x8
      mov  x28, x25
    LBB0_11:
      ldr  d1, [x24], #8
      fadd  d0, d0, d1
      blr  x27
      str  d0, [x19], #8
      subs  x28, x28, #1
      b.ne  LBB0_11
      b  LBB0_3
    LBB0_12:
      ldr  x8, [sp, #16]
      str  xzr, [x8]
      mov  w0, #0
      ldp  x29, x30, [sp, #128]
      ldp  x20, x19, [sp, #112]
      ldp  x22, x21, [sp, #96]
      ldp  x24, x23, [sp, #80]
      ldp  x26, x25, [sp, #64]
      ldp  x28, x27, [sp, #48]
      ldp  d9, d8, [sp, #32]
      add  sp, sp, #144
      ret
      .loh AdrpLdrGot  Lloh0, Lloh1
    ```
<!-- END generated: kernel-asm-fmod-structure -->

## Discussion

**The subtraction isolates exactly one call to libm's `fmod`.**

1. *Intended call, and nothing else*: the one structural addition is `+ blr %x1` — an indirect
   call through a register that holds the `fmod` address (loaded once, outside
   the loop). The `-`/`+` pairs on the `str`/`subs` lines are the canonical-index shift described on the [index page](index.md); the instructions themselves are identical.
2. *In the dependency chain*: the accumulator flows through the call — `fadd` produces the
   argument, the call returns the result the next iteration's `fadd` consumes. The divisor is the freshly loaded element, off the chain.
3. *Loop-structure symmetry*: same asymmetry as the [SQRT page](sqrt.md) — `f_add` unrolls 8×, `f_add_fmod` does not; the diff shows `f_add`'s scalar remainder. As there, both sides stay latency-bound through the accumulator chain, so the subtraction holds.
