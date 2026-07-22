# DIV

The `DIV` cost is the latency difference between a probe chaining two dependent divisions per
element and one chaining a single division — probes `f_div_div` and `f_div`.

What Python code counts into `DIV` is described in
[FLOP types](../flop_types.md#flop-div).

## Inner-loop diff

<!-- BEGIN generated: machine-code-div-diff -->
```diff
--- f_div
+++ f_div_div
  .L0:
  ldr  %d0, [%x0], #8
  fcmp  %d0, #0.0
  b.eq  .L1
  fdiv  %d1, %d1, %d0
+ fdiv  %d1, %d1, %d0
  str  %d1, [%x1], #8
  subs  %x2, %x2, #1
  b.ne  .L0
```
<!-- END generated: machine-code-div-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-div-structure -->
- `f_div` -- 1 innermost loop(s): 8 instructions
- `f_div_div` -- 1 innermost loop(s): 9 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'
amount of work -- see the discussion below.

??? note "Full ASM listing: `f_div`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_7
      cmp  x3, #1
      b.lt  LBB0_7
      ldr  x8, [sp, #56]
      ldr  x9, [sp]
      mov  x10, #22377
      movk  x10, #35604, lsl #16
      movk  x10, #48906, lsl #32
      movk  x10, #16389, lsl #48
      fmov  d0, x10
    LBB0_3:
      sub  x10, x2, #1
      mov  x11, x3
      mov  x12, x9
      mov  x13, x8
      mov.16b  v1, v0
    LBB0_4:
      ldr  d2, [x12], #8
      fcmp  d2, #0.0
      b.eq  LBB0_8
      fdiv  d1, d1, d2
      str  d1, [x13], #8
      subs  x11, x11, #1
      b.ne  LBB0_4
      cmp  x2, #1
      mov  x2, x10
      b.gt  LBB0_3
    LBB0_7:
      str  xzr, [x0]
      mov  w0, #0
      ret
    LBB0_8:
    Lloh0:
      adrp  x8, _.const.picklebuf.<addr>@GOTPAGE
    Lloh1:
      ldr  x8, [x8, _.const.picklebuf.<addr>@GOTPAGEOFF]
      str  x8, [x1]
      mov  w0, #1
      ret
      .loh AdrpLdrGot  Lloh0, Lloh1
    ```

??? note "Full ASM listing: `f_div_div`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_7
      cmp  x3, #1
      b.lt  LBB0_7
      ldr  x8, [sp, #56]
      ldr  x9, [sp]
      mov  x10, #22377
      movk  x10, #35604, lsl #16
      movk  x10, #48906, lsl #32
      movk  x10, #16389, lsl #48
      fmov  d0, x10
    LBB0_3:
      sub  x10, x2, #1
      mov  x11, x3
      mov  x12, x9
      mov  x13, x8
      mov.16b  v1, v0
    LBB0_4:
      ldr  d2, [x12], #8
      fcmp  d2, #0.0
      b.eq  LBB0_8
      fdiv  d1, d1, d2
      fdiv  d1, d1, d2
      str  d1, [x13], #8
      subs  x11, x11, #1
      b.ne  LBB0_4
      cmp  x2, #1
      mov  x2, x10
      b.gt  LBB0_3
    LBB0_7:
      str  xzr, [x0]
      mov  w0, #0
      ret
    LBB0_8:
    Lloh0:
      adrp  x8, _.const.picklebuf.<addr>@GOTPAGE
    Lloh1:
      ldr  x8, [x8, _.const.picklebuf.<addr>@GOTPAGEOFF]
      str  x8, [x1]
      mov  w0, #1
      ret
      .loh AdrpLdrGot  Lloh0, Lloh1
    ```
<!-- END generated: machine-code-div-structure -->

## Discussion

**The subtraction isolates exactly one `fdiv`.**

1. *Intended instruction, and nothing else*: the diff is the single line `+ fdiv %d1, %d1, %d0`.
   The `fcmp`/`b.eq` pair visible in both loops is numba's divide-by-zero guard (Python
   semantics raise on `x / 0.0`); it is identical on both sides and cancels in the subtraction.
2. *In the dependency chain*: both divisions read and write the accumulator, so each element
   pays two dependent `fdiv` latencies instead of one.
3. *Loop-structure symmetry*: **symmetric.** Both probes compile to a single scalar loop —
   the guard branch keeps LLVM from unrolling either side.
