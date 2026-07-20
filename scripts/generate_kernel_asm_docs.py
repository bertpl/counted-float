"""Regenerate the benchmark-kernel machine-code listings committed under docs/kernel_asm/.

Every benchmarked flop cost is a *difference* of two kernel latencies, which silently assumes the
compiler emitted exactly the intended extra work. The pages under `docs/kernel_asm/` make that
assumption inspectable: per flop cost, the compiled inner loops of the two kernels are shown as a
unified diff, together with each kernel's loop structure, so a reader can verify the measurement
isolates what its name claims. The prose discussion on each page is hand-written; this script only
rewrites the marked listing blocks (same marker mechanism as `generate_docs_content.py`).

Run via `make regen-kernel-asm` whenever a kernel, numba, or LLVM changes the generated code.

Unlike the dataset-derived docs content, these listings are machine-code and therefore
architecture-specific: the committed pages are generated on ARM64 (Apple M-series), and the script
refuses to run anywhere else so a regen on another machine cannot silently swap the architecture
out from under the committed pages. The drift test skips on other platforms for the same reason.

What "inner loop" means here: each kernel is a doubly-nested loop; the listings show every
*innermost* loop of the kernel's compiled native function -- a backward branch to a label with no
other label in between. LLVM may compile one source loop into several such loops (e.g. an
8x-unrolled main loop plus a scalar remainder loop), which is exactly the kind of structural
asymmetry these pages exist to surface, so all of them are listed. The diff shows the
best-matching pair of loops across the two kernels.

Registers and labels are canonicalized (in order of first appearance) before diffing, so a diff
line means a structural difference, never LLVM's register allocator picking different names.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import platform
import re
import sys
from pathlib import Path

import numpy as np

# sibling script, not a package: make its marked-block engine importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_docs_content import _read_lf, rewrite_marked_blocks

REPO_ROOT = Path(__file__).resolve().parent.parent
KERNEL_ASM_DOCS_DIR = REPO_ROOT / "docs" / "kernel_asm"

# The architecture the committed listings are generated on; pages state it in prose.
REQUIRED_MACHINE = "arm64"

_LABEL_RE = re.compile(r"^(LBB\d+_\d+):")
_BRANCH_TO_LABEL_RE = re.compile(r"^\t(?:b(?:\.\w+)?|cbz|cbnz|tbz|tbnz)\t.*?(LBB\d+_\d+)$")
_LABEL_REF_RE = re.compile(r"LBB\d+_\d+")
_REGISTER_RE = re.compile(r"\b([xwdsqv])(\d+)\b")


# ==================================================================================================
#  ASM parsing
# ==================================================================================================
def native_function_body(asm: str) -> list[str]:
    """The instruction lines of the first function in a numba ASM dump.

    numba emits the native nopython function first, followed by the cpython wrapper, the cfunc
    wrapper and runtime helpers -- everything after the native function is call-glue that never
    runs inside the timed loop, so only the first function body is of interest.
    """
    lines = asm.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("__ZN") and line.endswith(":"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith(".globl"))
    return lines[start + 1 : end]


def innermost_loops(body: list[str]) -> list[list[str]]:
    """Every innermost loop in `body`: label through backward branch, no label in between.

    Returns:
        The loop blocks in source order, each a list of raw ASM lines starting with the loop
        label and ending with the branch back to it.
    """
    label_positions = {match.group(1): i for i, line in enumerate(body) if (match := _LABEL_RE.match(line))}
    loops: list[list[str]] = []
    for i, line in enumerate(body):
        match = _BRANCH_TO_LABEL_RE.match(line.rstrip())
        if not match:
            continue
        target = label_positions.get(match.group(1))
        if target is None or target >= i:
            continue  # forward branch, not a loop
        block = body[target : i + 1]
        if not any(_LABEL_RE.match(inner) for inner in block[1:]):
            loops.append(block)
    return loops


def canonicalize_loop(block: list[str]) -> list[str]:
    """Rename registers and labels to appearance-ordered canonical names, for diffability.

    GPRs keep their width letter (`x`/`w`) but share one numbering per underlying register, and
    FPRs (`d`/`s`/`q`/`v`) likewise, so e.g. the third distinct float register is always `%d2`
    no matter which physical register the allocator picked. Special names (`sp`, `xzr`, ...)
    carry no allocator choice and stay as-is.
    """
    gpr_indices: dict[str, str] = {}
    fpr_indices: dict[str, str] = {}
    label_names: dict[str, str] = {}

    def rename_register(match: re.Match[str]) -> str:
        kind, number = match.groups()
        indices = gpr_indices if kind in "xw" else fpr_indices
        indices.setdefault(number, str(len(indices)))
        return f"%{kind}{indices[number]}"

    out: list[str] = []
    for line in block:
        for label in _LABEL_REF_RE.findall(line):
            label_names.setdefault(label, f".L{len(label_names)}")
        renamed = _REGISTER_RE.sub(rename_register, line)
        for label, canonical in label_names.items():
            renamed = renamed.replace(label, canonical)
        out.append(re.sub(r"\t", "  ", renamed.strip()))
    return out


# ==================================================================================================
#  Kernel compilation
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class CompiledKernel:
    """One benchmark kernel's compiled native function, in the two forms the pages show.

    Attributes:
        loops: The canonicalized innermost loops, for diffing.
        full_listing: The complete native-function ASM, raw as numba emits it, for the
            collapsible full listing.
    """

    loops: list[list[str]]
    full_listing: list[str]


def compile_kernel(kernel_name: str) -> CompiledKernel:
    """Compile one benchmark kernel with the suite's signature and dissect its ASM."""
    from counted_float._core.benchmarking.flops import _flops_kernels as kernels

    kernel = getattr(kernels, kernel_name)
    size = 16
    kernel(1, size, np.linspace(1.0, 2.0, size), np.zeros(size), np.zeros(size, dtype=np.int64))
    asm = kernel.inspect_asm(next(iter(kernel.signatures)))
    body = native_function_body(asm)
    return CompiledKernel(
        loops=[canonicalize_loop(loop) for loop in innermost_loops(body)],
        full_listing=[_stabilize_symbols(line.replace("\t", "  ").rstrip()) for line in body],
    )


def _stabilize_symbols(line: str) -> str:
    """Strip the per-process address suffix from numba's constant symbols.

    Kernels with an error path (e.g. the scaled hypot/dist kernels' zero-maximum guard) reference
    constants numba names `_.const.<name>.<address>`; the address changes every process, which
    would make the committed listings flap on every regen.
    """
    return re.sub(r"(_\.const\.\w+)\.\d+", r"\1.<addr>", line)


# ==================================================================================================
#  Page-block rendering
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class KernelAsmPage:
    """One flop cost's page: the kernel pair whose latency difference prices it.

    Attributes:
        doc_name: Page file name under docs/kernel_asm/, without extension.
        kind: The overview page's grouping bucket the flop cost belongs to.
        base_kernel: The subtracted kernel (diff "before" side).
        extended_kernel: The kernel carrying the extra operation (diff "after" side).
    """

    doc_name: str
    kind: str
    base_kernel: str
    extended_kernel: str


# The overview page's grouping buckets, in display order.
KIND_HARDWARE = "Hardware instructions"
KIND_LIBM = "Library calls (libm)"
KIND_ARITY = "Arity-scaled algorithms"
KINDS: list[str] = [KIND_HARDWARE, KIND_LIBM, KIND_ARITY]

# The exemplar pages, spanning the distinct kernel shapes: a bare arithmetic instruction (SQRT),
# a libm call (LOG), a chained-base pair (EXP), and an arity-scaled pair (HYPOT_XARG).
PAGES: list[KernelAsmPage] = [
    KernelAsmPage("sqrt", kind=KIND_HARDWARE, base_kernel="f_add", extended_kernel="f_add_sqrt"),
    KernelAsmPage("log", kind=KIND_LIBM, base_kernel="f_add", extended_kernel="f_add_log"),
    KernelAsmPage("exp", kind=KIND_LIBM, base_kernel="f_add_log", extended_kernel="f_add_log_exp"),
    KernelAsmPage(
        "hypot_xarg", kind=KIND_ARITY, base_kernel="f_add_hypot_scaled2", extended_kernel="f_add_hypot_scaled8"
    ),
]


def best_matching_loops(base_loops: list[list[str]], extended_loops: list[list[str]]) -> tuple[list[str], list[str]]:
    """The pair of loops (one per kernel) with the highest line-level similarity.

    When a kernel compiles to several innermost loops (unrolled main + remainder), the remainder
    is the one structurally comparable to the other kernel's loop -- highest-similarity selection
    finds it without hard-coding which kernel unrolled.
    """
    _, base, extended = max(
        (difflib.SequenceMatcher(a=base, b=extended).ratio(), base, extended)
        for base in base_loops
        for extended in extended_loops
    )
    return base, extended


def render_diff_block(page: KernelAsmPage, base: list[str], extended: list[str]) -> str:
    """The unified diff of the best-matching loop pair, as a `diff`-fenced markdown block."""
    body: list[str] = []
    for tag, a_lo, a_hi, b_lo, b_hi in difflib.SequenceMatcher(a=base, b=extended).get_opcodes():
        if tag in ("equal", "delete", "replace"):
            body.extend(f"  {line}" if tag == "equal" else f"- {line}" for line in base[a_lo:a_hi])
        if tag in ("insert", "replace"):
            body.extend(f"+ {line}" for line in extended[b_lo:b_hi])
    return "\n".join(["```diff", f"--- {page.base_kernel}", f"+++ {page.extended_kernel}", *body, "```"])


def render_structure_block(page: KernelAsmPage, kernels_by_name: dict[str, CompiledKernel]) -> str:
    """Each kernel's innermost-loop inventory, with the full function ASM behind a collapsible.

    The inventory line is the at-a-glance unrolling check (one loop vs. main + remainder); the
    collapsed complete listings let a reader verify the diffed loop was not cherry-picked and
    that nothing relevant sits outside it.
    """
    inventory = [
        f"- `{name}` -- {len(compiled.loops)} innermost loop(s): "
        + ", ".join(f"{len(loop)} instructions" for loop in compiled.loops)
        for name, compiled in kernels_by_name.items()
    ]
    intro = [
        "The listings below are the complete compiled functions the benchmark times, raw as numba",
        "emits them (the cpython call wrappers around them are omitted -- they never run inside the",
        "timed loop). Listing lengths reflect the compiler's unrolling choices, not the kernels'",
        "amount of work -- see the discussion below.",
    ]
    listings: list[str] = []
    for name, compiled in kernels_by_name.items():
        listing_lines = "\n".join(compiled.full_listing).rstrip("\n").split("\n")
        listings.append(f'??? note "Full ASM listing: `{name}`"')
        listings.append("    ```asm")
        listings.extend(f"    {line}".rstrip() for line in listing_lines)
        listings.append("    ```")
        listings.append("")
    return "\n".join([*inventory, "", *intro, "", *listings]).rstrip()


def render_page_list_block() -> str:
    """The overview page's grouped links to the per-cost pages, alphabetical within each group."""
    lines: list[str] = []
    for kind in KINDS:
        pages = sorted((page for page in PAGES if page.kind == kind), key=lambda page: page.doc_name)
        if not pages:
            continue
        lines.append(f"**{kind}**")
        lines.append("")
        lines.extend(f"- [{page.doc_name.upper()}]({page.doc_name}.md)" for page in pages)
        lines.append("")
    return "\n".join(lines).rstrip()


def regenerate_pages() -> dict[Path, str]:
    """Regenerate every page's marked blocks; returns the intended full content per page file."""
    kernel_cache: dict[str, CompiledKernel] = {}

    def compiled(kernel_name: str) -> CompiledKernel:
        if kernel_name not in kernel_cache:
            kernel_cache[kernel_name] = compile_kernel(kernel_name)
        return kernel_cache[kernel_name]

    regenerated: dict[Path, str] = {}
    for page in PAGES:
        base_kernel, extended_kernel = compiled(page.base_kernel), compiled(page.extended_kernel)
        base, extended = best_matching_loops(base_kernel.loops, extended_kernel.loops)
        marker_stem = f"kernel-asm-{page.doc_name.replace('_', '-')}"
        replacements = {
            f"{marker_stem}-diff": render_diff_block(page, base, extended),
            f"{marker_stem}-structure": render_structure_block(
                page, {page.base_kernel: base_kernel, page.extended_kernel: extended_kernel}
            ),
        }
        file_path = KERNEL_ASM_DOCS_DIR / f"{page.doc_name}.md"
        regenerated[file_path] = rewrite_marked_blocks(_read_lf(file_path), file_path, replacements)
    index_path = KERNEL_ASM_DOCS_DIR / "index.md"
    regenerated[index_path] = rewrite_marked_blocks(
        _read_lf(index_path), index_path, {"kernel-asm-page-list": render_page_list_block()}
    )
    return regenerated


# ==================================================================================================
#  Entry point
# ==================================================================================================
def main() -> int:
    """Regenerate the kernel ASM listing blocks; `--check` verifies instead of writing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on stale listings, write nothing")
    args = parser.parse_args()

    if platform.machine() != REQUIRED_MACHINE:
        sys.stderr.write(
            f"kernel ASM listings are committed as {REQUIRED_MACHINE} machine code; "
            f"refusing to regenerate on '{platform.machine()}' -- see module docstring\n"
        )
        return 1

    regenerated = regenerate_pages()
    if args.check:
        stale = [path for path, intended in regenerated.items() if _read_lf(path) != intended]
        for path in stale:
            sys.stderr.write(f"stale kernel ASM listings in {path.relative_to(REPO_ROOT)}\n")
        if stale:
            sys.stderr.write("run `make regen-kernel-asm`\n")
            return 1
        return 0

    for file_path, intended in regenerated.items():
        if _read_lf(file_path) != intended:
            file_path.write_text(intended, encoding="utf-8", newline="\n")
            print(f"rewrote {file_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
