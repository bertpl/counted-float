# SUMPROD

The `SUMPROD` cost is the per-call base price of `math.sumprod`, measured as the latency
difference between a probe chaining the extended-precision sum of two 2-element products and
one chaining only `tmp + x[i]` — probes `f_add_sumprod2` and `f_add`. Together with
[SUMPROD_XELEM](sumprod_xelem.md) (the per-extra-element slope) it prices `sumprod` at any
length. The probe is a faithful port of the compensated (TripleLength) accumulation CPython's
`math.sumprod` runs on exact-float inputs: per element a `dl_mul` error-free product — the
error term a genuine fused multiply-add, emitted through the `llvm.fma` intrinsic — folded
into a three-double running total, plus the close-out collapsing that total to one double.
The compensated sequence has real instruction-level parallelism (only the hi-lane
accumulation is serial), which is why the cost is measured on the whole algorithm rather than
decomposed into a per-operation chain — see [Cost-model principles](../cost_model.md).

What Python code counts into `SUMPROD` is described in
[FLOP types](../flop_types.md#flop-sumprod).

## Inner-loop diff

<!-- BEGIN generated: machine-code-sumprod-diff -->
```diff
--- f_add
+++ f_add_sumprod2
  .L0:
- ldr  %d0, [%x0], #8
- fadd  %d1, %d1, %d0
- str  %d1, [%x1], #8
- subs  %x2, %x2, #1
+ ldr  %d0, [%x0, #8]!
+ fmul  %d1, %d0, %d2
+ fadd  %d3, %d3, %d0
+ ldr  %d0, [%x1]
+ fmul  %d4, %d3, %d0
+ fnmsub  %d3, %d3, %d0, %d4
+ fadd  %d0, %d1, %d4
+ fsub  %d5, %d0, %d1
+ fsub  %d6, %d0, %d5
+ fsub  %d6, %d1, %d6
+ fsub  %d4, %d4, %d5
+ fadd  %d4, %d4, %d6
+ fadd  %d5, %d1, %d3
+ fsub  %d6, %d5, %d1
+ fsub  %d7, %d5, %d6
+ fsub  %d7, %d1, %d7
+ fsub  %d3, %d3, %d6
+ fadd  %d3, %d3, %d7
+ fadd  %d6, %d5, %d4
+ fsub  %d7, %d6, %d5
+ fsub  %d8, %d6, %d7
+ fsub  %d5, %d5, %d8
+ fsub  %d4, %d4, %d7
+ fadd  %d4, %d4, %d5
+ fadd  %d3, %d3, %d4
+ fadd  %d3, %d1, %d3
+ ldp  %d4, %d1, [%x1, #-16]
+ fmul  %d5, %d1, %d4
+ fnmsub  %d1, %d1, %d4, %d5
+ fadd  %d4, %d0, %d5
+ fsub  %d7, %d4, %d0
+ fsub  %d8, %d4, %d7
+ fsub  %d0, %d0, %d8
+ fsub  %d5, %d5, %d7
+ fadd  %d0, %d5, %d0
+ fadd  %d5, %d1, %d6
+ fsub  %d7, %d5, %d6
+ fsub  %d8, %d5, %d7
+ fsub  %d6, %d6, %d8
+ fsub  %d1, %d1, %d7
+ fadd  %d1, %d1, %d6
+ fadd  %d6, %d5, %d0
+ fsub  %d7, %d6, %d5
+ fsub  %d8, %d6, %d7
+ fsub  %d5, %d5, %d8
+ fsub  %d0, %d0, %d7
+ fadd  %d0, %d0, %d5
+ fadd  %d0, %d1, %d0
+ fadd  %d3, %d3, %d0
+ fadd  %d0, %d4, %d6
+ fsub  %d1, %d0, %d6
+ fsub  %d5, %d0, %d1
+ fsub  %d5, %d6, %d5
+ fsub  %d1, %d4, %d1
+ fadd  %d1, %d1, %d5
+ fadd  %d3, %d1, %d3
+ fadd  %d3, %d0, %d3
+ str  %d3, [%x2], #8
+ mov  %x1, %x0
+ subs  %x3, %x3, #1
  b.ne  .L0
```
<!-- END generated: machine-code-sumprod-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-sumprod-structure -->
- `f_add` -- 2 innermost loop(s): 30 instructions, 6 instructions
- `f_add_sumprod2` -- 2 innermost loop(s): 65 instructions, 62 instructions

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

??? note "Full ASM listing: `f_add_sumprod2`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_9
      cmp  x3, #1
      b.lt  LBB0_9
      ldr  x8, [sp, #56]
      ldp  x10, x9, [sp]
      sub  x11, x10, #8
      sub  x12, x10, #16
      sub  x13, x10, #24
      movi.2d  v0, #0000000000000000
      mov  x14, #22377
      movk  x14, #35604, lsl #16
      movk  x14, #48906, lsl #32
      movk  x14, #16389, lsl #48
      fmov  d1, x14
      b  LBB0_4
    LBB0_3:
      subs  x2, x2, #1
      b.le  LBB0_9
    LBB0_4:
      ldr  d2, [x10]
      fmul  d3, d2, d0
      fadd  d2, d2, d1
      ldr  d4, [x11, x9, lsl #3]
      fmul  d5, d2, d4
      fnmsub  d2, d2, d4, d5
      fadd  d4, d3, d5
      fsub  d6, d4, d3
      fsub  d7, d4, d6
      fsub  d7, d3, d7
      fsub  d5, d5, d6
      fadd  d5, d5, d7
      fadd  d6, d3, d2
      fsub  d7, d6, d3
      fsub  d16, d6, d7
      fsub  d16, d3, d16
      fsub  d2, d2, d7
      fadd  d2, d2, d16
      fadd  d7, d6, d5
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      fsub  d6, d6, d17
      fsub  d5, d5, d16
      fadd  d5, d5, d6
      fadd  d2, d2, d5
      fadd  d2, d3, d2
      ldr  d3, [x12, x9, lsl #3]
      ldr  d5, [x13, x9, lsl #3]
      fmul  d6, d3, d5
      fnmsub  d3, d3, d5, d6
      fadd  d5, d4, d6
      fsub  d16, d5, d4
      fsub  d17, d5, d16
      fsub  d4, d4, d17
      fsub  d6, d6, d16
      fadd  d4, d6, d4
      fadd  d6, d3, d7
      fsub  d16, d6, d7
      fsub  d17, d6, d16
      fsub  d7, d7, d17
      fsub  d3, d3, d16
      fadd  d3, d3, d7
      fadd  d7, d6, d4
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      fsub  d6, d6, d17
      fsub  d4, d4, d16
      fadd  d4, d4, d6
      fadd  d3, d3, d4
      fadd  d2, d2, d3
      fadd  d3, d5, d7
      fsub  d4, d3, d7
      fsub  d6, d3, d4
      fsub  d6, d7, d6
      fsub  d4, d5, d4
      fadd  d4, d4, d6
      fadd  d2, d4, d2
      fadd  d2, d3, d2
      str  d2, [x8]
      cmp  x3, #1
      b.eq  LBB0_3
      ldp  d4, d3, [x10]
      fmul  d5, d3, d0
      fadd  d2, d2, d3
      fmul  d3, d2, d4
      fnmsub  d2, d2, d4, d3
      fadd  d4, d5, d3
      fsub  d6, d4, d5
      fsub  d7, d4, d6
      fsub  d7, d5, d7
      fsub  d3, d3, d6
      fadd  d3, d3, d7
      fadd  d6, d5, d2
      fsub  d7, d6, d5
      fsub  d16, d6, d7
      fsub  d16, d5, d16
      fsub  d2, d2, d7
      fadd  d2, d2, d16
      fadd  d7, d6, d3
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      fsub  d6, d6, d17
      fsub  d3, d3, d16
      fadd  d3, d3, d6
      fadd  d2, d2, d3
      fadd  d2, d5, d2
      ldr  d3, [x11, x9, lsl #3]
      ldr  d5, [x12, x9, lsl #3]
      fmul  d6, d3, d5
      fnmsub  d3, d3, d5, d6
      fadd  d5, d4, d6
      fsub  d16, d5, d4
      fsub  d17, d5, d16
      fsub  d4, d4, d17
      fsub  d6, d6, d16
      fadd  d4, d6, d4
      fadd  d6, d3, d7
      fsub  d16, d6, d7
      fsub  d17, d6, d16
      fsub  d7, d7, d17
      fsub  d3, d3, d16
      fadd  d3, d3, d7
      fadd  d7, d6, d4
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      fsub  d6, d6, d17
      fsub  d4, d4, d16
      fadd  d4, d4, d6
      fadd  d3, d3, d4
      fadd  d2, d2, d3
      fadd  d3, d5, d7
      fsub  d4, d3, d7
      fsub  d6, d3, d4
      fsub  d6, d7, d6
      fsub  d4, d5, d4
      fadd  d4, d4, d6
      fadd  d2, d4, d2
      fadd  d2, d3, d2
      str  d2, [x8, #8]
      cmp  x3, #2
      b.eq  LBB0_3
      ldp  d3, d5, [x10, #8]
      fmul  d4, d5, d0
      fadd  d2, d2, d5
      ldr  d5, [x10]
      fmul  d6, d2, d3
      fnmsub  d2, d2, d3, d6
      fadd  d3, d4, d6
      fsub  d7, d3, d4
      fsub  d16, d3, d7
      fsub  d16, d4, d16
      fsub  d6, d6, d7
      fadd  d6, d6, d16
      fadd  d7, d4, d2
      fsub  d16, d7, d4
      fsub  d17, d7, d16
      fsub  d17, d4, d17
      fsub  d2, d2, d16
      fadd  d2, d2, d17
      fadd  d16, d7, d6
      fsub  d17, d16, d7
      fsub  d18, d16, d17
      fsub  d7, d7, d18
      fsub  d6, d6, d17
      fadd  d6, d6, d7
      fadd  d2, d2, d6
      fadd  d2, d4, d2
      ldr  d4, [x11, x9, lsl #3]
      fmul  d6, d5, d4
      fnmsub  d4, d5, d4, d6
      fadd  d5, d3, d6
      fsub  d7, d5, d3
      fsub  d17, d5, d7
      fsub  d3, d3, d17
      fsub  d6, d6, d7
      fadd  d3, d6, d3
      fadd  d6, d4, d16
      fsub  d7, d6, d16
      fsub  d17, d6, d7
      fsub  d16, d16, d17
      fsub  d4, d4, d7
      fadd  d4, d4, d16
      fadd  d7, d6, d3
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      fsub  d6, d6, d17
      fsub  d3, d3, d16
      fadd  d3, d3, d6
      fadd  d3, d4, d3
      fadd  d2, d2, d3
      fadd  d3, d5, d7
      fsub  d4, d3, d7
      fsub  d6, d3, d4
      fsub  d6, d7, d6
      fsub  d4, d5, d4
      fadd  d4, d4, d6
      fadd  d2, d4, d2
      fadd  d2, d3, d2
      str  d2, [x8, #16]
      cmp  x3, #3
      b.eq  LBB0_3
      add  x17, x10, #16
      sub  x14, x3, #3
      add  x15, x8, #24
      mov  x16, x17
    LBB0_8:
      ldr  d3, [x16, #8]!
      fmul  d4, d3, d0
      fadd  d2, d2, d3
      ldr  d3, [x17]
      fmul  d5, d2, d3
      fnmsub  d2, d2, d3, d5
      fadd  d3, d4, d5
      fsub  d6, d3, d4
      fsub  d7, d3, d6
      fsub  d7, d4, d7
      fsub  d5, d5, d6
      fadd  d5, d5, d7
      fadd  d6, d4, d2
      fsub  d7, d6, d4
      fsub  d16, d6, d7
      fsub  d16, d4, d16
      fsub  d2, d2, d7
      fadd  d2, d2, d16
      fadd  d7, d6, d5
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      fsub  d6, d6, d17
      fsub  d5, d5, d16
      fadd  d5, d5, d6
      fadd  d2, d2, d5
      fadd  d2, d4, d2
      ldp  d5, d4, [x17, #-16]
      fmul  d6, d4, d5
      fnmsub  d4, d4, d5, d6
      fadd  d5, d3, d6
      fsub  d16, d5, d3
      fsub  d17, d5, d16
      fsub  d3, d3, d17
      fsub  d6, d6, d16
      fadd  d3, d6, d3
      fadd  d6, d4, d7
      fsub  d16, d6, d7
      fsub  d17, d6, d16
      fsub  d7, d7, d17
      fsub  d4, d4, d16
      fadd  d4, d4, d7
      fadd  d7, d6, d3
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      fsub  d6, d6, d17
      fsub  d3, d3, d16
      fadd  d3, d3, d6
      fadd  d3, d4, d3
      fadd  d2, d2, d3
      fadd  d3, d5, d7
      fsub  d4, d3, d7
      fsub  d6, d3, d4
      fsub  d6, d7, d6
      fsub  d4, d5, d4
      fadd  d4, d4, d6
      fadd  d2, d4, d2
      fadd  d2, d3, d2
      str  d2, [x15], #8
      mov  x17, x16
      subs  x14, x14, #1
      b.ne  LBB0_8
      b  LBB0_3
    LBB0_9:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```
<!-- END generated: machine-code-sumprod-structure -->

## Discussion

**The subtraction isolates the whole 2-element compensated sum-of-products — inline code, no
library call.**

1. *What the diff shows*: on top of `f_add`'s load/`fadd` skeleton, the additions are the
   algorithm itself. Per element: the product (`fmul`), its error term as a single fused
   `fnmsub` (LLVM lowers `fma(x, y, -hi)` to one fused negate-multiply-subtract), and three
   six-instruction error-free sums (`fadd`/`fsub` ladders) folding the pair into the
   three-double running total. After both elements, the close-out: one more error-free sum
   plus the two final adds. The extra `fmul` against a constant zero is the probe's guard
   against constant folding: the accumulator starts from a runtime zero, so LLVM cannot fold
   the first element's compensated arithmetic the way CPython's runtime zeros never would be.
2. *In the dependency chain*: the hi-lane accumulation serializes across the two elements and
   through the close-out, whose result feeds the next iteration's first product. The lo and
   tiny lanes run beside it — the algorithm's genuine instruction-level parallelism — so the
   measurement prices the algorithm as it really executes, not a serialized per-operation
   decomposition (which is exactly why `SUMPROD` is measured rather than decomposed).
3. *Loop-structure symmetry*: `f_add` unrolls 8×; the sumprod loop, far larger, does not.
   Its two regions are the peeled first iteration (where the negative wraparound indices need
   separate handling) and the steady state. Both sides remain latency-bound, so the
   subtraction holds.
