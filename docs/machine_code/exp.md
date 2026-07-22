# EXP

The `EXP` cost is the latency difference between a probe chaining `exp(log(tmp + x[i]))` and one
chaining `log(tmp + x[i])` — probes `f_add_log_exp` and `f_add_log`. Exemplar of a **chained-base
pair**: `exp` grows without bound, so a plain `exp` chain would overflow; instead `log` bounds the
argument, and the `log`-only probe is subtracted so its cost cancels.

What Python code counts into `EXP` is described in
[FLOP types](../flop_types.md#flop-exp).

## Inner-loop diff

<!-- BEGIN generated: machine-code-exp-diff -->
```diff
--- f_add_log
+++ f_add_log_exp
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
<!-- END generated: machine-code-exp-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-exp-structure -->
- `f_add_log` -- 1 innermost loop(s): 7 instructions
- `f_add_log_exp` -- 1 innermost loop(s): 8 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_add_log`"
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
      adrp  x24, _log@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _log@GOTPAGEOFF]
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

??? note "Full ASM listing: `f_add_log_exp`"
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
      adrp  x24, _log@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _log@GOTPAGEOFF]
    Lloh2:
      adrp  x25, _exp@GOTPAGE
    Lloh3:
      ldr  x25, [x25, _exp@GOTPAGEOFF]
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
<!-- END generated: machine-code-exp-structure -->

## Discussion

**The subtraction isolates exactly one call to libm's `exp`.**

1. *Intended call, and nothing else*: the one structural addition is the second `blr` —
   `f_add_log`'s loop contains one indirect libm call (`log`), `f_add_log_exp`'s contains two
   (`log`, then `exp`), each through its own preloaded call-target register. The remaining
   `-`/`+` pairs are the canonical-index shift described on the [index page](index.md).
2. *In the dependency chain*: the calls are back-to-back on the accumulator — `log`'s return
   value is `exp`'s argument, whose return value feeds the next iteration's `fadd` — so each
   iteration pays the full add→log→exp latency and the subtraction leaves exactly the `exp` leg.
3. *Loop-structure symmetry*: **symmetric.** Both probes compile to a single scalar loop (7 vs 8
   instructions) — this is the cleanest of the exemplar shapes, since neither side unrolls.
