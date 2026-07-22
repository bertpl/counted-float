# EXP10

The `EXP10` cost is the latency difference between a probe chaining
`10 ** log10(tmp + x[i])` and one chaining `log10(tmp + x[i])` — probes `f_add_log10_exp10`
and `f_add_log10`. Chained-base pair, like [EXP](exp.md) — with one twist worth knowing.

What Python code counts into `EXP10` is described in
[FLOP types](../flop_types.md#flop-exp10).

## Inner-loop diff

<!-- BEGIN generated: machine-code-exp10-diff -->
```diff
--- f_add_log10
+++ f_add_log10_exp10
  .L0:
  ldr  %d0, [%x0], #8
  fadd  %d1, %d1, %d0
  blr  %x1
- str  %d1, [%x2], #8
- subs  %x3, %x3, #1
+ mov.16b  %v0, %v1
+ fmov  %d1, #10.00000000
+ blr  %x2
+ str  %d1, [%x3], #8
+ subs  %x4, %x4, #1
  b.ne  .L0
```
<!-- END generated: machine-code-exp10-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-exp10-structure -->
- `f_add_log10` -- 1 innermost loop(s): 7 instructions
- `f_add_log10_exp10` -- 1 innermost loop(s): 10 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_add_log10`"
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
      adrp  x24, _log10@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _log10@GOTPAGEOFF]
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

??? note "Full ASM listing: `f_add_log10_exp10`"
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
      adrp  x24, _log10@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _log10@GOTPAGEOFF]
    Lloh2:
      adrp  x25, _pow@GOTPAGE
    Lloh3:
      ldr  x25, [x25, _pow@GOTPAGEOFF]
    LBB0_3:
      mov  x26, x20
      mov  x27, x23
      mov  x28, x22
      mov.16b  v0, v8
    LBB0_4:
      ldr  d1, [x27], #8
      fadd  d0, d0, d1
      blr  x24
      mov.16b  v1, v0
      fmov  d0, #10.00000000
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
<!-- END generated: machine-code-exp10-structure -->

## Discussion

**The subtraction isolates one call to libm's `pow` with the base fixed at 10 — `exp10` is
not standard C (some libms carry it as an extension; macOS's does not), so `10 ** x` lowers
to `pow(10.0, x)`.**

1. *What the diff shows*: the additions are the `pow` call plus its argument setup — a register
   move and `fmov %d1, #10.0` materializing the constant base each iteration. Both setup
   instructions are negligible against the call itself, but they are part of what the weight
   measures. So `EXP10` prices "raise 10 to a power" as Python actually executes it, which may
   run slower than a hand-rolled `exp(x * log(10))`.
2. *In the dependency chain*: `log10`'s return value becomes `pow`'s exponent argument, so the
   calls serialize on the accumulator and the subtraction leaves exactly the `pow` leg.
3. *Loop-structure symmetry*: **symmetric.** Both probes compile to a single scalar loop.
