# HYPOT

The `HYPOT` cost is the latency difference between a probe chaining `math.hypot(tmp + x[i])` and
one chaining only `tmp + x[i]` — probes `f_add_hypot` and `f_add`. Like most libm-backed functions,
`math.hypot` compiles to a call into the math library. This is the two-argument libm form (the per-extra-coordinate slope of the n-ary form is priced separately as `HYPOT_XARG`).

What Python code counts into `HYPOT` is described in
[FLOP types](../flop_types.md#flop-hypot). Why the 2-argument form is measured on the real libm call while the n-ary slope is hand-rolled is covered in the [benchmark design rationale](../analysis_methodology.md#16-benchmark-design-rationale).

## Inner-loop diff

<!-- BEGIN generated: machine-code-hypot-diff -->
```diff
--- f_add
+++ f_add_hypot
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
<!-- END generated: machine-code-hypot-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-hypot-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_hypot` -- 1 innermost loop(s): 7 instructions

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

??? note "Full ASM listing: `f_add_hypot`"
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
      adrp  x24, _hypot@GOTPAGE
    Lloh1:
      ldr  x24, [x24, _hypot@GOTPAGEOFF]
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
      b.hi  LBB0_3
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
      .cfi_endproc
    ```
<!-- END generated: machine-code-hypot-structure -->

## Discussion

**The subtraction isolates exactly one call to libm's `hypot`.**

1. *Intended call, and nothing else*: the one structural addition is `+ blr %x1` — an indirect
   call through a register that holds the `hypot` address (loaded once, outside
   the loop). The `-`/`+` pairs on the `str`/`subs` lines are the canonical-index shift described on the [index page](index.md); the instructions themselves are identical.
2. *In the dependency chain*: the accumulator flows through the call — `fadd` produces the
   argument, the call returns the result the next iteration's `fadd` consumes. The second argument is the freshly loaded element, off the chain.
3. *Loop-structure symmetry*: same asymmetry as the [SQRT page](sqrt.md) — `f_add` unrolls 8×, `f_add_hypot` does not; the diff shows `f_add`'s scalar remainder. As there, both sides stay latency-bound through the accumulator chain, so the subtraction holds.
