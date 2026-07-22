# POW

The `POW` cost is the latency difference between a probe chaining two dependent
exponentiations per element and one chaining a single exponentiation — probes `f_pow_pow` and
`f_pow`. `tmp ** x[i]` compiles to a call to libm's `pow`.

What Python code counts into `POW` is described in
[FLOP types](../flop_types.md#flop-pow).

## Inner-loop diff

<!-- BEGIN generated: machine-code-pow-diff -->
```diff
--- f_pow
+++ f_pow_pow
  .L0:
- ldur  %d0, [%x0, #-32]
+ ldur  %d0, [%x0, #-8]
+ mov.16b  %v1, %v0
  blr  %x1
- stur  %d1, [%x2, #-32]
- ldur  %d0, [%x0, #-24]
+ mov.16b  %v1, %v0
  blr  %x1
- stur  %d1, [%x2, #-24]
- ldur  %d0, [%x0, #-16]
+ stur  %d2, [%x2, #-8]
+ add  %x3, %x3, #2
+ ldr  %d0, [%x0], #16
+ mov.16b  %v1, %v0
  blr  %x1
- stur  %d1, [%x2, #-16]
- ldur  %d0, [%x0, #-8]
+ mov.16b  %v1, %v0
  blr  %x1
- stur  %d1, [%x2, #-8]
- ldr  %d0, [%x0]
- blr  %x1
- str  %d1, [%x2]
- ldr  %d0, [%x0, #8]
- blr  %x1
- str  %d1, [%x2, #8]
- ldr  %d0, [%x0, #16]
- blr  %x1
- str  %d1, [%x2, #16]
- ldr  %d0, [%x0, #24]
- blr  %x1
- str  %d1, [%x2, #24]
- add  %x2, %x2, #64
- add  %x0, %x0, #64
- add  %x3, %x3, #8
+ str  %d2, [%x2], #16
  cmp  %x4, %x3
  b.ne  .L0
```
<!-- END generated: machine-code-pow-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-pow-structure -->
- `f_pow` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_pow_pow` -- 2 innermost loop(s): 16 instructions, 16 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_pow`"
    ```asm
      sub  sp, sp, #128
      stp  d9, d8, [sp, #16]
      stp  x28, x27, [sp, #32]
      stp  x26, x25, [sp, #48]
      stp  x24, x23, [sp, #64]
      stp  x22, x21, [sp, #80]
      stp  x20, x19, [sp, #96]
      stp  x29, x30, [sp, #112]
      str  x0, [sp, #8]
      cmp  x2, #1
      b.lt  LBB0_11
      subs  x21, x3, #1
      b.lt  LBB0_11
      mov  x20, x2
      ldr  x22, [sp, #184]
      ldr  x23, [sp, #128]
      and  x24, x3, #0x7
      and  x25, x3, #0x7ffffffffffffff8
      mov  x8, #22377
      movk  x8, #35604, lsl #16
      movk  x8, #48906, lsl #32
      movk  x8, #16389, lsl #48
      fmov  d8, x8
    Lloh0:
      adrp  x26, _pow@GOTPAGE
    Lloh1:
      ldr  x26, [x26, _pow@GOTPAGEOFF]
      b  LBB0_4
    LBB0_3:
      subs  x20, x20, #1
      b.le  LBB0_11
    LBB0_4:
      cmp  x21, #7
      b.hs  LBB0_6
      mov  x27, #0
      mov.16b  v0, v8
      b  LBB0_9
    LBB0_6:
      mov  x27, #0
      add  x28, x23, #32
      add  x19, x22, #32
      mov.16b  v0, v8
    LBB0_7:
      ldur  d1, [x28, #-32]
      blr  x26
      stur  d0, [x19, #-32]
      ldur  d1, [x28, #-24]
      blr  x26
      stur  d0, [x19, #-24]
      ldur  d1, [x28, #-16]
      blr  x26
      stur  d0, [x19, #-16]
      ldur  d1, [x28, #-8]
      blr  x26
      stur  d0, [x19, #-8]
      ldr  d1, [x28]
      blr  x26
      str  d0, [x19]
      ldr  d1, [x28, #8]
      blr  x26
      str  d0, [x19, #8]
      ldr  d1, [x28, #16]
      blr  x26
      str  d0, [x19, #16]
      ldr  d1, [x28, #24]
      blr  x26
      str  d0, [x19, #24]
      add  x19, x19, #64
      add  x28, x28, #64
      add  x27, x27, #8
      cmp  x25, x27
      b.ne  LBB0_7
      cbz  x24, LBB0_3
    LBB0_9:
      lsl  x8, x27, #3
      add  x19, x22, x8
      add  x27, x23, x8
      mov  x28, x24
    LBB0_10:
      ldr  d1, [x27], #8
      blr  x26
      str  d0, [x19], #8
      subs  x28, x28, #1
      b.ne  LBB0_10
      b  LBB0_3
    LBB0_11:
      ldr  x8, [sp, #8]
      str  xzr, [x8]
      mov  w0, #0
      ldp  x29, x30, [sp, #112]
      ldp  x20, x19, [sp, #96]
      ldp  x22, x21, [sp, #80]
      ldp  x24, x23, [sp, #64]
      ldp  x26, x25, [sp, #48]
      ldp  x28, x27, [sp, #32]
      ldp  d9, d8, [sp, #16]
      add  sp, sp, #128
      ret
      .loh AdrpLdrGot  Lloh0, Lloh1
    ```

??? note "Full ASM listing: `f_pow_pow`"
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
      fmov  d9, x8
    Lloh0:
      adrp  x25, _pow@GOTPAGE
    Lloh1:
      ldr  x25, [x25, _pow@GOTPAGEOFF]
      b  LBB0_6
    LBB0_3:
      mov  x26, #0
      mov.16b  v0, v9
    LBB0_4:
      ldr  d8, [x23, x26, lsl #3]
      mov.16b  v1, v8
      blr  x25
      mov.16b  v1, v8
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
      mov.16b  v0, v9
    LBB0_8:
      ldur  d8, [x28, #-8]
      mov.16b  v1, v8
      blr  x25
      mov.16b  v1, v8
      blr  x25
      stur  d0, [x27, #-8]
      add  x26, x26, #2
      ldr  d8, [x28], #16
      mov.16b  v1, v8
      blr  x25
      mov.16b  v1, v8
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
<!-- END generated: machine-code-pow-structure -->

## Discussion

**The subtraction isolates one extra chained `pow` call per element.**

1. *Intended call, and nothing else*: per element, `f_pow_pow` makes two dependent `pow` calls
   where `f_pow` makes one — the added `blr` lines, each preceded by a register move arranging
   the base/exponent arguments. The remaining `-`/`+` pairs are addressing differences between
   the two unrolling shapes (see point 3), not extra work.
2. *In the dependency chain*: the first call's result is the second call's base, so each
   element pays two dependent call latencies instead of one; the difference is one call.
3. *Loop-structure symmetry*: **not symmetric, deliberately surfaced** — `f_pow` compiles to an
   8×-unrolled main loop plus a scalar remainder (unusually for a call-bearing loop), while
   `f_pow_pow` compiles 2×-unrolled. The diff therefore aligns loops of different unrolling
   depth, which is what scatters the addressing lines. Both sides serialize through the
   accumulator across the calls, so per-element latency is unaffected and the subtraction
   holds.
