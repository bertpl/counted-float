"""The kernel ASM extraction must find the right loops and canonicalize them deterministically."""

import importlib.util
import sys
from pathlib import Path

_GENERATOR = Path(__file__).resolve().parent.parent.parent / "scripts" / "generate_kernel_asm_docs.py"
_spec = importlib.util.spec_from_file_location("generate_kernel_asm_docs", _GENERATOR)
generate_kernel_asm_docs = importlib.util.module_from_spec(_spec)
# registered before executing: dataclass field resolution looks the defining module up in
# sys.modules, which a bare module_from_spec import would leave absent
sys.modules[_spec.name] = generate_kernel_asm_docs
_spec.loader.exec_module(generate_kernel_asm_docs)

best_matching_loops = generate_kernel_asm_docs.best_matching_loops
canonicalize_loop = generate_kernel_asm_docs.canonicalize_loop
innermost_loops = generate_kernel_asm_docs.innermost_loops
native_function_body = generate_kernel_asm_docs.native_function_body

# A hand-written miniature of numba's ASM dump shape: the native function first, then the cpython
# wrapper (which must be excluded), with an outer loop wrapping an inner one (only the inner is an
# innermost loop) and a forward branch (not a loop at all).
_ASM = """\t.section\t__TEXT,__text
\t.globl\t__ZN8testfuncE
__ZN8testfuncE:
\tcmp\tx2, #1
\tb.lt\tLBB0_5
LBB0_1:
\tmov\tx10, x3
LBB0_2:
\tldr\td2, [x11], #8
\tfadd\td1, d1, d2
\tsubs\tx10, x10, #1
\tb.ne\tLBB0_2
\tsubs\tx2, x2, #1
\tb.gt\tLBB0_1
LBB0_5:
\tret
\t.globl\t__ZN7cpython8testfuncE
__ZN7cpython8testfuncE:
\tbl\t_PyArg_UnpackTuple
\tret
"""


def test_kernel_pages_cover_every_benchmarked_flop_type():
    # --- arrange -----------------------------------------
    from counted_float._core.models import FlopType

    # F2I / I2F have no benchmark kernels (their weights come from spec sheets and third-party
    # tables only), so they are the only FlopTypes without a machine-code page
    expected = {flop_type.name.lower() for flop_type in FlopType} - {"f2i", "i2f"}

    # --- act ---------------------------------------------
    page_names = {page.doc_name for page in generate_kernel_asm_docs.PAGES}

    # --- assert ------------------------------------------
    assert page_names == expected


def test_native_function_body_excludes_the_cpython_wrapper():
    # --- act ---------------------------------------------
    body = native_function_body(_ASM)

    # --- assert ------------------------------------------
    assert body[0] == "\tcmp\tx2, #1"
    assert body[-1] == "\tret"
    assert not any("PyArg" in line for line in body)


def test_innermost_loops_finds_only_the_label_free_backward_branch_block():
    # --- act ---------------------------------------------
    loops = innermost_loops(native_function_body(_ASM))

    # --- assert ------------------------------------------
    # the outer loop (LBB0_1) contains the inner label, so only the inner block qualifies
    assert [loop[0] for loop in loops] == ["LBB0_2:"]
    assert loops[0][-1] == "\tb.ne\tLBB0_2"
    assert len(loops[0]) == 5


def test_innermost_loops_merges_overlapping_spans_of_a_rotated_loop():
    # --- arrange -----------------------------------------
    # a rotated loop (cbrt-like shape): two backward branches whose spans overlap without
    # nesting -- one cycle, so one merged region is expected
    body = [
        "LBB0_3:",
        "\tsubs\tx21, x21, #1",
        "\tb.le\tLBB0_11",
        "LBB0_5:",
        "\tblr\tx24",
        "LBB0_6:",
        "\tstr\td0, [x27], #8",
        "\tb.eq\tLBB0_3",
        "LBB0_7:",
        "\tfadd\td0, d0, d1",
        "\tb.ge\tLBB0_5",
    ]

    # --- act ---------------------------------------------
    loops = innermost_loops(body)

    # --- assert ------------------------------------------
    assert len(loops) == 1
    assert loops[0][0] == "LBB0_3:"
    assert loops[0][-1] == "\tb.ge\tLBB0_5"


def test_canonicalize_loop_renames_registers_and_labels_by_first_appearance():
    # --- arrange -----------------------------------------
    loop = ["LBB0_7:", "\tldr\td2, [x11], #8", "\tfadd\td1, d1, d2", "\tb.ne\tLBB0_7"]

    # --- act ---------------------------------------------
    canonical = canonicalize_loop(loop)

    # --- assert ------------------------------------------
    # d2 is the first float register seen (index 0), d1 the second; x11 the first general-purpose
    # register; the label becomes .L0
    assert canonical == [".L0:", "ldr  %d0, [%x0], #8", "fadd  %d1, %d1, %d0", "b.ne  .L0"]


def test_canonicalize_loop_keeps_width_letters_but_shares_numbering_per_register():
    # --- arrange -----------------------------------------
    # w8 and x8 are the same underlying register accessed at two widths: same index, own letter
    loop = ["\tmov\tw8, #1", "\tadd\tx8, x8, x9"]

    # --- act ---------------------------------------------
    canonical = canonicalize_loop(loop)

    # --- assert ------------------------------------------
    assert canonical == ["mov  %w0, #1", "add  %x0, %x0, %x1"]


def test_best_matching_loops_picks_the_structurally_closest_pair():
    # --- arrange -----------------------------------------
    remainder = ["ldr", "fadd", "str", "b.ne"]
    unrolled_main = ["ldur", "fadd", "stur"] * 8
    extended = ["ldr", "fadd", "fsqrt", "str", "b.ne"]

    # --- act ---------------------------------------------
    base, matched = best_matching_loops([unrolled_main, remainder], [extended])

    # --- assert ------------------------------------------
    assert base == remainder
    assert matched == extended
