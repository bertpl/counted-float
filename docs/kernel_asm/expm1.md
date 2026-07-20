# EXPM1

The `EXPM1` cost is the latency difference between a kernel chaining
`expm1(log1p(tmp + x[i]))` and one chaining `log1p(tmp + x[i])` — kernels
`f_add_log1p_expm1` and `f_add_log1p`. Chained-base pair: `log1p` is `expm1`'s inverse,
keeping the chain bounded, and the `log1p`-only kernel is subtracted so its cost cancels.

What Python code counts into `EXPM1` is described in
[FLOP types](../flop_types.md#flop-expm1).

## Inner-loop diff

<!-- BEGIN generated: kernel-asm-expm1-diff -->
```diff
--- f_add_log1p
+++ f_add_log1p_expm1
  .L0:
  ldr  %d0, [%x0], #8
  fadd  %d1, %d1, %d0
  blr  %x1
- str  %d1, [%x2], #8
- subs  %x3, %x3, #1
+ blr  %x2
+ str  %d1, [%x3], #8
+ subs  %x4, %x4, #1
  b.ne  .L0
```
<!-- END generated: kernel-asm-expm1-diff -->

## Loop structure

<!-- BEGIN generated: kernel-asm-expm1-structure -->
- `f_add_log1p` -- 1 innermost loop(s): 7 instructions
- `f_add_log1p_expm1` -- 1 innermost loop(s): 8 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the kernels'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_add_log1p`"
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
      b.lt  LBB0_6
      mov  x20, x3
      cmp  x3, #1
      b.lt  LBB0_6
      mov  x21, x2
      ldr  x22, [sp, #168]
      ldr  x23, [sp, #112]
      mov  x8, #22377
      movk  x8, #35604, lsl #16
      movk  x8, #48906, lsl #32
      movk  x8, #16389, lsl #48
      fmov  d8, x8
    Lloh0:
      adrp  x24, _log1p@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _log1p@GOTPAGEOFF]
    LBB0_3:
      mov  x25, x20
      mov  x26, x23
      mov  x27, x22
      mov.16b  v0, v8
    LBB0_4:
      ldr  d1, [x26], #8
      fadd  d0, d0, d1
      blr  x24
      str  d0, [x27], #8
      subs  x25, x25, #1
      b.ne  LBB0_4
      subs  x21, x21, #1
      b.gt  LBB0_3
    LBB0_6:
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

??? note "Full ASM listing: `f_add_log1p_expm1`"
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
      b.lt  LBB0_6
      mov  x20, x3
      cmp  x3, #1
      b.lt  LBB0_6
      mov  x21, x2
      ldr  x22, [sp, #168]
      ldr  x23, [sp, #112]
      mov  x8, #22377
      movk  x8, #35604, lsl #16
      movk  x8, #48906, lsl #32
      movk  x8, #16389, lsl #48
      fmov  d8, x8
    Lloh0:
      adrp  x24, _log1p@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _log1p@GOTPAGEOFF]
    Lloh2:
      adrp  x25, _expm1@GOTPAGE
    Lloh3:
      ldr  x25, [x25, _expm1@GOTPAGEOFF]
    LBB0_3:
      mov  x26, x20
      mov  x27, x23
      mov  x28, x22
      mov.16b  v0, v8
    LBB0_4:
      ldr  d1, [x27], #8
      fadd  d0, d0, d1
      blr  x24
      blr  x25
      str  d0, [x28], #8
      subs  x26, x26, #1
      b.ne  LBB0_4
      subs  x21, x21, #1
      b.gt  LBB0_3
    LBB0_6:
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
      .loh AdrpLdrGot  Lloh2, Lloh3
      .loh AdrpLdrGot  Lloh0, Lloh1
    ```
<!-- END generated: kernel-asm-expm1-structure -->

## Discussion

**The subtraction isolates exactly one call to libm's `expm1`.**

1. *Intended call, and nothing else*: the one structural addition is the extra `blr` — the call
   into `expm1`, through its own preloaded call-target register. The `-`/`+` pairs on the `str`/`subs` lines are the canonical-index shift described on the [index page](index.md); the instructions themselves are identical.
2. *In the dependency chain*: the calls are back-to-back on the accumulator — `log1p`'s return value is `expm1`'s argument — so the subtraction leaves exactly the `expm1` leg.
3. *Loop-structure symmetry*: **symmetric.** Both kernels compile to a single scalar loop —
   neither side unrolls, so the subtraction cancels everything but the added call.
