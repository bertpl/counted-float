# SUMPROD_XELEM

The `SUMPROD_XELEM` cost is the per-extra-element slope of the extended-precision `sumprod`
algorithm: the latency difference between its 8-element and 2-element forms — probes
`f_add_sumprod8` and `f_add_sumprod2` — divided by the 6 extra elements. Exemplar of the same
construction as [DIST_XARG](dist_xarg.md) and [HYPOT_XARG](hypot_xarg.md): the two sides are
the same algorithm at two sizes, so the diff is expected to be large — what must hold is that
every added line belongs to the six extra elements, and nothing shared changed shape. Both
probes port CPython's compensated (TripleLength) accumulation, error terms emitted through
the `llvm.fma` intrinsic — see the [SUMPROD page](sumprod.md) for the algorithm.

## Inner-loop diff

<!-- BEGIN generated: machine-code-sumprod-xelem-diff -->
```diff
--- f_add_sumprod2
+++ f_add_sumprod8
  .L0:
- ldr  %d0, [%x0, #8]!
+ lsl  %x0, %x1, #3
+ add  %x2, %x3, %x0
+ ldr  %d0, [%x2]
  fmul  %d1, %d0, %d2
+ cmp  %x1, #0
+ csel  %x4, %x5, xzr, eq
  fadd  %d3, %d3, %d0
- ldr  %d0, [%x1]
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d0, [%x4, #-8]
  fmul  %d4, %d3, %d0
  fnmsub  %d3, %d3, %d0, %d4
  fadd  %d0, %d1, %d4
  fsub  %d5, %d0, %d1
  fsub  %d6, %d0, %d5
  fsub  %d6, %d1, %d6
  fsub  %d4, %d4, %d5
+ fadd  %d5, %d1, %d3
+ fsub  %d7, %d5, %d1
  fadd  %d4, %d4, %d6
- fadd  %d5, %d1, %d3
- fsub  %d6, %d5, %d1
- fsub  %d7, %d5, %d6
- fsub  %d7, %d1, %d7
- fsub  %d3, %d3, %d6
- fadd  %d3, %d3, %d7
+ fsub  %d6, %d5, %d7
+ fsub  %d6, %d1, %d6
+ fsub  %d3, %d3, %d7
+ fadd  %d3, %d3, %d6
  fadd  %d6, %d5, %d4
  fsub  %d7, %d6, %d5
  fsub  %d8, %d6, %d7
+ cmp  %x1, #2
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d9, [%x4, #-16]
+ fsub  %d4, %d4, %d7
+ cmp  %x1, #3
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d7, [%x4, #-24]
+ fmul  %d10, %d9, %d7
  fsub  %d5, %d5, %d8
+ fnmsub  %d7, %d9, %d7, %d10
+ fadd  %d8, %d0, %d10
+ fsub  %d9, %d8, %d0
+ fsub  %d11, %d8, %d9
+ fsub  %d0, %d0, %d11
+ fadd  %d4, %d4, %d5
+ fsub  %d5, %d10, %d9
+ fadd  %d0, %d5, %d0
+ fadd  %d5, %d7, %d6
+ fsub  %d9, %d5, %d6
+ fsub  %d10, %d5, %d9
+ fadd  %d3, %d3, %d4
+ fsub  %d4, %d6, %d10
+ fsub  %d6, %d7, %d9
+ fadd  %d7, %d5, %d0
+ fsub  %d9, %d7, %d5
+ fsub  %d10, %d7, %d9
+ fadd  %d4, %d6, %d4
+ fsub  %d0, %d0, %d9
+ cmp  %x1, #4
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d6, [%x4, #-32]
+ fsub  %d5, %d5, %d10
+ cmp  %x1, #5
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d9, [%x4, #-40]
+ fmul  %d10, %d6, %d9
+ fadd  %d1, %d1, %d3
+ fnmsub  %d3, %d6, %d9, %d10
+ fadd  %d6, %d8, %d10
+ fsub  %d9, %d6, %d8
+ fsub  %d11, %d6, %d9
+ fsub  %d8, %d8, %d11
+ fadd  %d0, %d0, %d5
+ fsub  %d5, %d10, %d9
+ fadd  %d5, %d5, %d8
+ fadd  %d8, %d3, %d7
+ fsub  %d9, %d8, %d7
+ fsub  %d10, %d8, %d9
+ fadd  %d0, %d4, %d0
+ fsub  %d4, %d7, %d10
+ fsub  %d3, %d3, %d9
+ fadd  %d7, %d8, %d5
+ fsub  %d9, %d7, %d8
+ fsub  %d10, %d7, %d9
+ fadd  %d3, %d3, %d4
+ fsub  %d4, %d5, %d9
+ cmp  %x1, #6
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d5, [%x4, #-48]
+ fsub  %d8, %d8, %d10
+ cmp  %x1, #7
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d9, [%x4, #-56]
+ fmul  %d10, %d5, %d9
+ fadd  %d1, %d1, %d0
+ fnmsub  %d0, %d5, %d9, %d10
+ fadd  %d5, %d6, %d10
+ fsub  %d9, %d5, %d6
+ fsub  %d11, %d5, %d9
+ fsub  %d6, %d6, %d11
+ fadd  %d4, %d4, %d8
+ fsub  %d8, %d10, %d9
+ fadd  %d6, %d8, %d6
+ fadd  %d8, %d0, %d7
+ fsub  %d9, %d8, %d7
+ fsub  %d10, %d8, %d9
+ fadd  %d3, %d3, %d4
+ fsub  %d4, %d7, %d10
+ fsub  %d0, %d0, %d9
+ fadd  %d7, %d8, %d6
+ fsub  %d9, %d7, %d8
+ fsub  %d10, %d7, %d9
+ fadd  %d0, %d0, %d4
+ fsub  %d4, %d6, %d9
+ cmp  %x1, #8
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d6, [%x4, #-64]
+ fsub  %d8, %d8, %d10
+ cmp  %x1, #9
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d9, [%x4, #-72]
+ fmul  %d10, %d6, %d9
+ fadd  %d1, %d1, %d3
+ fnmsub  %d3, %d6, %d9, %d10
+ fadd  %d6, %d5, %d10
+ fsub  %d9, %d6, %d5
+ fsub  %d11, %d6, %d9
+ fsub  %d5, %d5, %d11
+ fadd  %d4, %d4, %d8
+ fsub  %d8, %d10, %d9
+ fadd  %d5, %d8, %d5
+ fadd  %d8, %d3, %d7
+ fsub  %d9, %d8, %d7
+ fsub  %d10, %d8, %d9
+ fadd  %d0, %d0, %d4
+ fsub  %d4, %d7, %d10
+ fsub  %d3, %d3, %d9
+ fadd  %d7, %d8, %d5
+ fsub  %d9, %d7, %d8
+ fsub  %d10, %d7, %d9
+ fadd  %d3, %d3, %d4
+ fsub  %d4, %d5, %d9
+ cmp  %x1, #10
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d5, [%x4, #-80]
+ fsub  %d8, %d8, %d10
+ cmp  %x1, #11
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d9, [%x4, #-88]
+ fmul  %d10, %d5, %d9
+ fadd  %d1, %d1, %d0
+ fnmsub  %d0, %d5, %d9, %d10
+ fadd  %d5, %d6, %d10
+ fsub  %d9, %d5, %d6
+ fsub  %d11, %d5, %d9
+ fsub  %d6, %d6, %d11
+ fadd  %d4, %d4, %d8
+ fsub  %d8, %d10, %d9
+ fadd  %d6, %d8, %d6
+ fadd  %d8, %d0, %d7
+ fsub  %d9, %d8, %d7
+ fsub  %d10, %d8, %d9
+ fadd  %d3, %d3, %d4
+ fsub  %d4, %d7, %d10
+ fsub  %d0, %d0, %d9
+ fadd  %d7, %d8, %d6
+ fsub  %d9, %d7, %d8
+ fsub  %d10, %d7, %d9
+ fadd  %d0, %d0, %d4
+ fsub  %d4, %d6, %d9
+ cmp  %x1, #12
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d6, [%x4, #-96]
+ fsub  %d8, %d8, %d10
+ cmp  %x1, #13
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d9, [%x4, #-104]
+ fmul  %d10, %d6, %d9
+ fadd  %d1, %d1, %d3
+ fnmsub  %d3, %d6, %d9, %d10
+ fadd  %d6, %d5, %d10
+ fsub  %d9, %d6, %d5
+ fsub  %d11, %d6, %d9
+ fsub  %d5, %d5, %d11
+ fadd  %d4, %d4, %d8
+ fsub  %d8, %d10, %d9
+ fadd  %d5, %d8, %d5
+ fadd  %d8, %d3, %d7
+ fsub  %d9, %d8, %d7
+ fsub  %d10, %d8, %d9
+ fadd  %d0, %d0, %d4
+ fsub  %d4, %d7, %d10
+ fsub  %d3, %d3, %d9
+ fadd  %d7, %d8, %d5
+ fsub  %d9, %d7, %d8
+ fsub  %d10, %d7, %d9
+ fadd  %d3, %d3, %d4
+ fsub  %d4, %d5, %d9
+ cmp  %x1, #14
+ csel  %x4, %x5, xzr, lo
+ add  %x4, %x2, %x4, lsl #3
+ ldur  %d5, [%x4, #-112]
+ fsub  %d8, %d8, %d10
+ cmp  %x1, #15
+ csel  %x4, %x5, xzr, lo
+ add  %x2, %x2, %x4, lsl #3
+ ldur  %d9, [%x2, #-120]
+ fmul  %d10, %d5, %d9
+ fadd  %d1, %d1, %d0
+ fnmsub  %d0, %d5, %d9, %d10
+ fadd  %d5, %d6, %d10
+ fsub  %d9, %d5, %d6
+ fsub  %d11, %d5, %d9
+ fsub  %d6, %d6, %d11
+ fadd  %d4, %d4, %d8
+ fsub  %d8, %d10, %d9
+ fadd  %d6, %d8, %d6
+ fadd  %d8, %d0, %d7
+ fsub  %d9, %d8, %d7
+ fsub  %d10, %d8, %d9
+ fadd  %d3, %d3, %d4
+ fsub  %d4, %d7, %d10
+ add  %x1, %x1, #1
+ fsub  %d0, %d0, %d9
+ fadd  %d0, %d0, %d4
+ fadd  %d4, %d8, %d6
+ fadd  %d1, %d1, %d3
+ fsub  %d3, %d4, %d8
+ fsub  %d7, %d4, %d3
+ fsub  %d7, %d8, %d7
+ fsub  %d3, %d6, %d3
+ fadd  %d3, %d3, %d7
+ fadd  %d3, %d0, %d3
+ fadd  %d0, %d5, %d4
+ fsub  %d6, %d0, %d4
+ fsub  %d7, %d0, %d6
  fsub  %d4, %d4, %d7
- fadd  %d4, %d4, %d5
- fadd  %d3, %d3, %d4
- fadd  %d3, %d1, %d3
- ldp  %d4, %d1, [%x1, #-16]
- fmul  %d5, %d1, %d4
- fnmsub  %d1, %d1, %d4, %d5
- fadd  %d4, %d0, %d5
- fsub  %d7, %d4, %d0
- fsub  %d8, %d4, %d7
- fsub  %d0, %d0, %d8
- fsub  %d5, %d5, %d7
- fadd  %d0, %d5, %d0
- fadd  %d5, %d1, %d6
- fsub  %d7, %d5, %d6
- fsub  %d8, %d5, %d7
- fsub  %d6, %d6, %d8
- fsub  %d1, %d1, %d7
- fadd  %d1, %d1, %d6
- fadd  %d6, %d5, %d0
- fsub  %d7, %d6, %d5
- fsub  %d8, %d6, %d7
- fsub  %d5, %d5, %d8
- fsub  %d0, %d0, %d7
- fadd  %d0, %d0, %d5
- fadd  %d0, %d1, %d0
- fadd  %d3, %d3, %d0
- fadd  %d0, %d4, %d6
- fsub  %d1, %d0, %d6
- fsub  %d5, %d0, %d1
- fsub  %d5, %d6, %d5
- fsub  %d1, %d4, %d1
- fadd  %d1, %d1, %d5
- fadd  %d3, %d1, %d3
- fadd  %d3, %d0, %d3
- str  %d3, [%x2], #8
- mov  %x1, %x0
- subs  %x3, %x3, #1
+ fsub  %d5, %d5, %d6
+ fadd  %d1, %d1, %d3
+ fadd  %d3, %d5, %d4
+ fadd  %d1, %d3, %d1
+ fadd  %d3, %d0, %d1
+ str  %d3, [%x6, %x0]
+ cmp  %x7, %x1
  b.ne  .L0
```
<!-- END generated: machine-code-sumprod-xelem-diff -->

## Loop structure

<!-- BEGIN generated: machine-code-sumprod-xelem-structure -->
- `f_add_sumprod2` -- 2 innermost loop(s): 65 instructions, 62 instructions
- `f_add_sumprod8` -- 1 innermost loop(s): 254 instructions

The listings below are the complete compiled functions the benchmark times, raw as numba
emits them (the cpython call wrappers around them are omitted -- they never run inside the
timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'
amount of work -- see the discussion below.

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

??? note "Full ASM listing: `f_add_sumprod8`"
    ```asm
      cmp  x2, #1
      b.lt  LBB0_6
      cmp  x3, #1
      b.lt  LBB0_6
      ldr  x8, [sp, #56]
      ldp  x10, x9, [sp]
      mov  x11, #22377
      movk  x11, #35604, lsl #16
      movk  x11, #48906, lsl #32
      movk  x11, #16389, lsl #48
      fmov  d0, x11
      movi.2d  v1, #0000000000000000
    LBB0_3:
      mov  x12, #0
      mov.16b  v3, v0
    LBB0_4:
      lsl  x11, x12, #3
      add  x13, x10, x11
      ldr  d4, [x13]
      fmul  d2, d4, d1
      cmp  x12, #0
      csel  x14, x9, xzr, eq
      fadd  d3, d3, d4
      add  x14, x13, x14, lsl #3
      ldur  d4, [x14, #-8]
      fmul  d5, d3, d4
      fnmsub  d3, d3, d4, d5
      fadd  d4, d2, d5
      fsub  d6, d4, d2
      fsub  d7, d4, d6
      fsub  d7, d2, d7
      fsub  d5, d5, d6
      fadd  d6, d2, d3
      fsub  d16, d6, d2
      fadd  d5, d5, d7
      fsub  d7, d6, d16
      fsub  d7, d2, d7
      fsub  d3, d3, d16
      fadd  d3, d3, d7
      fadd  d7, d6, d5
      fsub  d16, d7, d6
      fsub  d17, d7, d16
      cmp  x12, #2
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d18, [x14, #-16]
      fsub  d5, d5, d16
      cmp  x12, #3
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d16, [x14, #-24]
      fmul  d19, d18, d16
      fsub  d6, d6, d17
      fnmsub  d16, d18, d16, d19
      fadd  d17, d4, d19
      fsub  d18, d17, d4
      fsub  d20, d17, d18
      fsub  d4, d4, d20
      fadd  d5, d5, d6
      fsub  d6, d19, d18
      fadd  d4, d6, d4
      fadd  d6, d16, d7
      fsub  d18, d6, d7
      fsub  d19, d6, d18
      fadd  d3, d3, d5
      fsub  d5, d7, d19
      fsub  d7, d16, d18
      fadd  d16, d6, d4
      fsub  d18, d16, d6
      fsub  d19, d16, d18
      fadd  d5, d7, d5
      fsub  d4, d4, d18
      cmp  x12, #4
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d7, [x14, #-32]
      fsub  d6, d6, d19
      cmp  x12, #5
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d18, [x14, #-40]
      fmul  d19, d7, d18
      fadd  d2, d2, d3
      fnmsub  d3, d7, d18, d19
      fadd  d7, d17, d19
      fsub  d18, d7, d17
      fsub  d20, d7, d18
      fsub  d17, d17, d20
      fadd  d4, d4, d6
      fsub  d6, d19, d18
      fadd  d6, d6, d17
      fadd  d17, d3, d16
      fsub  d18, d17, d16
      fsub  d19, d17, d18
      fadd  d4, d5, d4
      fsub  d5, d16, d19
      fsub  d3, d3, d18
      fadd  d16, d17, d6
      fsub  d18, d16, d17
      fsub  d19, d16, d18
      fadd  d3, d3, d5
      fsub  d5, d6, d18
      cmp  x12, #6
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d6, [x14, #-48]
      fsub  d17, d17, d19
      cmp  x12, #7
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d18, [x14, #-56]
      fmul  d19, d6, d18
      fadd  d2, d2, d4
      fnmsub  d4, d6, d18, d19
      fadd  d6, d7, d19
      fsub  d18, d6, d7
      fsub  d20, d6, d18
      fsub  d7, d7, d20
      fadd  d5, d5, d17
      fsub  d17, d19, d18
      fadd  d7, d17, d7
      fadd  d17, d4, d16
      fsub  d18, d17, d16
      fsub  d19, d17, d18
      fadd  d3, d3, d5
      fsub  d5, d16, d19
      fsub  d4, d4, d18
      fadd  d16, d17, d7
      fsub  d18, d16, d17
      fsub  d19, d16, d18
      fadd  d4, d4, d5
      fsub  d5, d7, d18
      cmp  x12, #8
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d7, [x14, #-64]
      fsub  d17, d17, d19
      cmp  x12, #9
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d18, [x14, #-72]
      fmul  d19, d7, d18
      fadd  d2, d2, d3
      fnmsub  d3, d7, d18, d19
      fadd  d7, d6, d19
      fsub  d18, d7, d6
      fsub  d20, d7, d18
      fsub  d6, d6, d20
      fadd  d5, d5, d17
      fsub  d17, d19, d18
      fadd  d6, d17, d6
      fadd  d17, d3, d16
      fsub  d18, d17, d16
      fsub  d19, d17, d18
      fadd  d4, d4, d5
      fsub  d5, d16, d19
      fsub  d3, d3, d18
      fadd  d16, d17, d6
      fsub  d18, d16, d17
      fsub  d19, d16, d18
      fadd  d3, d3, d5
      fsub  d5, d6, d18
      cmp  x12, #10
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d6, [x14, #-80]
      fsub  d17, d17, d19
      cmp  x12, #11
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d18, [x14, #-88]
      fmul  d19, d6, d18
      fadd  d2, d2, d4
      fnmsub  d4, d6, d18, d19
      fadd  d6, d7, d19
      fsub  d18, d6, d7
      fsub  d20, d6, d18
      fsub  d7, d7, d20
      fadd  d5, d5, d17
      fsub  d17, d19, d18
      fadd  d7, d17, d7
      fadd  d17, d4, d16
      fsub  d18, d17, d16
      fsub  d19, d17, d18
      fadd  d3, d3, d5
      fsub  d5, d16, d19
      fsub  d4, d4, d18
      fadd  d16, d17, d7
      fsub  d18, d16, d17
      fsub  d19, d16, d18
      fadd  d4, d4, d5
      fsub  d5, d7, d18
      cmp  x12, #12
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d7, [x14, #-96]
      fsub  d17, d17, d19
      cmp  x12, #13
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d18, [x14, #-104]
      fmul  d19, d7, d18
      fadd  d2, d2, d3
      fnmsub  d3, d7, d18, d19
      fadd  d7, d6, d19
      fsub  d18, d7, d6
      fsub  d20, d7, d18
      fsub  d6, d6, d20
      fadd  d5, d5, d17
      fsub  d17, d19, d18
      fadd  d6, d17, d6
      fadd  d17, d3, d16
      fsub  d18, d17, d16
      fsub  d19, d17, d18
      fadd  d4, d4, d5
      fsub  d5, d16, d19
      fsub  d3, d3, d18
      fadd  d16, d17, d6
      fsub  d18, d16, d17
      fsub  d19, d16, d18
      fadd  d3, d3, d5
      fsub  d5, d6, d18
      cmp  x12, #14
      csel  x14, x9, xzr, lo
      add  x14, x13, x14, lsl #3
      ldur  d6, [x14, #-112]
      fsub  d17, d17, d19
      cmp  x12, #15
      csel  x14, x9, xzr, lo
      add  x13, x13, x14, lsl #3
      ldur  d18, [x13, #-120]
      fmul  d19, d6, d18
      fadd  d2, d2, d4
      fnmsub  d4, d6, d18, d19
      fadd  d6, d7, d19
      fsub  d18, d6, d7
      fsub  d20, d6, d18
      fsub  d7, d7, d20
      fadd  d5, d5, d17
      fsub  d17, d19, d18
      fadd  d7, d17, d7
      fadd  d17, d4, d16
      fsub  d18, d17, d16
      fsub  d19, d17, d18
      fadd  d3, d3, d5
      fsub  d5, d16, d19
      add  x12, x12, #1
      fsub  d4, d4, d18
      fadd  d4, d4, d5
      fadd  d5, d17, d7
      fadd  d2, d2, d3
      fsub  d3, d5, d17
      fsub  d16, d5, d3
      fsub  d16, d17, d16
      fsub  d3, d7, d3
      fadd  d3, d3, d16
      fadd  d3, d4, d3
      fadd  d4, d6, d5
      fsub  d7, d4, d5
      fsub  d16, d4, d7
      fsub  d5, d5, d16
      fsub  d6, d6, d7
      fadd  d2, d2, d3
      fadd  d3, d6, d5
      fadd  d2, d3, d2
      fadd  d3, d4, d2
      str  d3, [x8, x11]
      cmp  x3, x12
      b.ne  LBB0_4
      subs  x2, x2, #1
      b.gt  LBB0_3
    LBB0_6:
      str  xzr, [x0]
      mov  w0, #0
      ret
    ```
<!-- END generated: machine-code-sumprod-xelem-structure -->

## Discussion

**The subtraction isolates six extra elements' worth of the compensated accumulation, and the
÷6 therefore prices one element.**

1. *Intended work, and nothing else*: per extra element, the additions decompose into two
   loads, the product and its fused error term (`fmul` + `fnmsub`), and the three
   six-instruction error-free sums folding the pair into the running total — six of each.
   The shared skeleton (the first element's product off the fed-back chain, the opaque-zero
   guard, the close-out, store, loop control) appears once on both sides.
2. *Integer-side asymmetry, off the measured chain*: the arity-8 loop materializes each
   wrapped negative index with a `cmp`/`csel`/`add` triple per load, where the arity-2 form's
   peeled first iteration lets the steady state use precomputed base pointers. That work runs
   on the integer ports, overlapping the floating-point chain — the same class of side traffic
   as the [REMAINDER](remainder.md) probe's per-iteration pointer reload — so the
   floating-point latency slope is unaffected.
3. *In the dependency chain*: the hi-lane accumulation lengthens proportionally with the
   element count while the lo/tiny lanes overlap it — the measured overlap is the algorithm's
   real instruction-level parallelism, and the reason the slope is priced as a unit rather
   than as a per-operation chain.
4. *Loop-structure symmetry*: neither probe unrolls; `f_add_sumprod2`'s two regions are its
   peeled first iteration plus steady state, while the arity-8 loop (carrying the `csel`
   index handling instead) compiles to a single region. The diff shows the best-matching
   region pair.
