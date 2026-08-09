"""Regenerate the benchmark-probe machine-code listings committed under docs/machine_code/.

Every benchmarked flop cost is a *difference* of two probe latencies, which silently assumes the
compiler emitted exactly the intended extra work. The pages under `docs/machine_code/` make that
assumption inspectable: per flop cost, the compiled inner loops of the two probes are shown as a
unified diff, together with each probe's loop structure, so a reader can verify the measurement
isolates what its name claims. The prose discussion on each page is hand-written; this script only
rewrites the marked listing blocks (same marker mechanism as `generate_docs_content.py`).

Run via `make regen-machine-code` whenever a probe, numba, or LLVM changes the generated code.

Unlike the dataset-derived docs content, these listings are machine-code and therefore
architecture-specific: the committed pages are generated on ARM64 (Apple M-series), and the script
refuses to run anywhere else so a regen on another machine cannot silently swap the architecture
out from under the committed pages. The drift test skips on other platforms for the same reason.

What "inner loop" means here: each probe is a doubly-nested loop; the listings show every
*innermost* loop of the probe's compiled native function -- a backward branch to a label with no
other label in between. LLVM may compile one source loop into several such loops (e.g. an
8x-unrolled main loop plus a scalar remainder loop), which is exactly the kind of structural
asymmetry these pages exist to surface, so all of them are listed. The diff shows the
best-matching pair of loops across the two probes.

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

# sibling package, not importable by default: make the marked-block engine reachable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_artifacts import read_lf, rewrite_marked_blocks

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINE_CODE_DOCS_DIR = REPO_ROOT / "docs" / "machine_code"

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
    """Every innermost loop region in `body`, from the backward branches' spans.

    A loop candidate is the span from a backward branch's target label through the branch line.
    Two reductions turn the candidates into presentable regions:

    - a candidate that strictly contains another candidate is an outer loop and is dropped;
    - candidates that overlap are merged into one region -- branchy probes compile to rotated
      loops whose cycle closes through forward branches and fallthrough (e.g. the cbrt probe's
      sign/NaN handling), yielding several overlapping backward spans that are really one loop.

    Returns:
        The loop regions in source order, each a list of raw ASM lines.
    """
    label_positions = {match.group(1): i for i, line in enumerate(body) if (match := _LABEL_RE.match(line))}
    spans: list[tuple[int, int]] = []
    for i, line in enumerate(body):
        match = _BRANCH_TO_LABEL_RE.match(line.rstrip())
        if not match:
            continue
        target = label_positions.get(match.group(1))
        if target is not None and target < i:
            spans.append((target, i))
    spans = [
        span
        for span in spans
        if not any(other != span and span[0] <= other[0] and other[1] <= span[1] for other in spans)
    ]
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return [body[start : end + 1] for start, end in merged]


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
#  Probe compilation
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class CompiledProbe:
    """One benchmark probe's compiled native function, in the two forms the pages show.

    Attributes:
        loops: The canonicalized innermost loops, for diffing.
        full_listing: The complete native-function ASM, raw as numba emits it, for the
            collapsible full listing.
    """

    loops: list[list[str]]
    full_listing: list[str]


def compile_probe(probe_name: str) -> CompiledProbe:
    """Compile one benchmark probe with the suite's signature and dissect its ASM."""
    from counted_float._core.benchmarking.flops import _flops_probes as probes

    probe = getattr(probes, probe_name)
    size = 16
    probe(1, size, np.linspace(1.0, 2.0, size), np.zeros(size), np.zeros(size, dtype=np.int64))
    asm = probe.inspect_asm(next(iter(probe.signatures)))
    body = native_function_body(asm)
    return CompiledProbe(
        loops=[canonicalize_loop(loop) for loop in innermost_loops(body)],
        full_listing=[_stabilize_symbols(line.replace("\t", "  ").rstrip()) for line in body],
    )


def _stabilize_symbols(line: str) -> str:
    """Strip the per-process address suffix from numba's generated symbols.

    Two symbol families carry a per-process address that would make the committed listings flap
    on every regen: the constants of probes with an error path (`_.const.<name>.<address>`, e.g.
    the scaled hypot/dist probes' zero-maximum guard) and the dynamic globals holding a ctypes
    function pointer (`_numba.dynamic.globals.<hex address>`, the remainder probe).
    """
    line = re.sub(r"(_\.const\.\w+)\.\d+", r"\1.<addr>", line)
    return re.sub(r"(_numba\.dynamic\.globals)\.[0-9a-f]+", r"\1.<addr>", line)


# ==================================================================================================
#  Page-block rendering
# ==================================================================================================
@dataclasses.dataclass(frozen=True)
class MachineCodePage:
    """One flop cost's page: the probe pair whose latency difference prices it.

    Attributes:
        doc_name: Page file name under docs/machine_code/, without extension.
        kind: The overview page's grouping bucket the flop cost belongs to.
        base_probe: The subtracted probe (diff "before" side).
        extended_probe: The probe carrying the extra operation (diff "after" side).
        rationale: Cost-model table note for grey-zone cases -- filled only where the pricing
            choice needs defending beyond the kind's default rule.
        range_sensitive: True where the benchmark's input range is load-bearing for the
            weight's validity (a why-comment in the benchmark source marks these); the
            cost-model table then lists rule 4 alongside the kind's default rule.
        probe_span: Extra coordinates or elements the extended probe carries over the base
            probe; a per-argument slope is their latency difference divided by that span. The
            default applies where the probes differ by an operation rather than by arity.
    """

    doc_name: str
    kind: str
    base_probe: str
    extended_probe: str
    rationale: str = ""
    range_sensitive: bool = False
    probe_span: int = 1


# The overview page's grouping buckets, in display order, and the cost-model rule each one
# defaults to (see docs/cost_model_rules.md for the rules' statements).
KIND_HARDWARE = "Hardware instructions"
KIND_LIBM = "Library calls (libm)"
KIND_ARITY = "Arity-scaled algorithms"
KINDS: list[str] = [KIND_HARDWARE, KIND_LIBM, KIND_ARITY]
RULE_BY_KIND: dict[str, str] = {KIND_HARDWARE: "1", KIND_LIBM: "2", KIND_ARITY: "2"}

# One page per benchmarked flop cost; the probe pairs mirror the subtractions in
# FlopsBenchmarkSuite.run()'s estimated_flop_latencies. COMP's true subtrahend is the average of
# the ADD and SUB single-op probes; its page diffs against f_add and explains the average.
PAGES: list[MachineCodePage] = [
    # --- hardware instructions -------------------
    MachineCodePage("abs", kind=KIND_HARDWARE, base_probe="f_add", extended_probe="f_add_abs"),
    MachineCodePage("add", kind=KIND_HARDWARE, base_probe="f_add", extended_probe="f_add_add"),
    MachineCodePage(
        "comp",
        kind=KIND_HARDWARE,
        base_probe="f_add",
        extended_probe="f_lte_addsub",
        rationale=(
            "rule 2 · fmax-shares-comp-weight, rule 3 · classifiers-price-their-question: "
            "the subtrahend is the ADD/SUB average, and the branchy source compiles branchless -- the weight prices "
            "compare-and-select machinery, matching what float comparisons cost in optimized code. "
            "`math.fmax`/`fmin` reuse this weight: their port -- the IEEE max/min instruction (ARM's "
            "`fmaxnm`/`fminnm`) -- is one instruction of the same compare-select class, the same reuse as "
            "`math.fabs` -> ABS. They stay a different value function from the builtin `min`/`max` (NaN-quieting "
            "selection vs a comparison chain returning whichever operand survives, order-dependent under NaN): "
            "shared machinery, and so a shared price, not shared semantics"
        ),
    ),
    MachineCodePage("copysign", kind=KIND_HARDWARE, base_probe="f_add", extended_probe="f_add_copysign"),
    MachineCodePage("div", kind=KIND_HARDWARE, base_probe="f_div", extended_probe="f_div_div"),
    MachineCodePage(
        "fma",
        kind=KIND_HARDWARE,
        base_probe="f_fma",
        extended_probe="f_fma_fma",
        rationale="rule 1 · fma-stays-as-written: the one fusion observable from Python, so the one that is counted",
    ),
    MachineCodePage("minus", kind=KIND_HARDWARE, base_probe="f_add", extended_probe="f_add_minus"),
    MachineCodePage("mul", kind=KIND_HARDWARE, base_probe="f_mul", extended_probe="f_mul_mul"),
    MachineCodePage("rnd", kind=KIND_HARDWARE, base_probe="f_add", extended_probe="f_add_round"),
    MachineCodePage("sqrt", kind=KIND_HARDWARE, base_probe="f_add", extended_probe="f_add_sqrt"),
    MachineCodePage("sub", kind=KIND_HARDWARE, base_probe="f_add", extended_probe="f_add_sub"),
    # --- library calls ---------------------------
    MachineCodePage("acos", kind=KIND_LIBM, base_probe="f_add_sin", extended_probe="f_add_sin_acos"),
    MachineCodePage("acosh", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_acosh", range_sensitive=True),
    MachineCodePage("asin", kind=KIND_LIBM, base_probe="f_add_sin", extended_probe="f_add_sin_asin"),
    MachineCodePage("asinh", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_asinh", range_sensitive=True),
    MachineCodePage("atan", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_atan", range_sensitive=True),
    MachineCodePage("atan2", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_atan2", range_sensitive=True),
    MachineCodePage("atanh", kind=KIND_LIBM, base_probe="f_add_halfsin", extended_probe="f_add_halfsin_atanh"),
    MachineCodePage(
        "cbrt",
        kind=KIND_LIBM,
        base_probe="f_add",
        extended_probe="f_add_cbrt",
        rationale=(
            "rule 2 · measurement-fallbacks: numba's `np.cbrt` wraps the libm call in NaN/sign handling "
            "CPython's `math.cbrt` never executes, "
            "so the probe calls libm through a ctypes binding -- the bare call CPython executes"
        ),
    ),
    MachineCodePage("cos", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_cos", range_sensitive=True),
    MachineCodePage(
        "cosh", kind=KIND_LIBM, base_probe="f_add_acosh", extended_probe="f_add_acosh_cosh", range_sensitive=True
    ),
    MachineCodePage("erf", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_erf", range_sensitive=True),
    MachineCodePage("erfc", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_erfc", range_sensitive=True),
    MachineCodePage("exp", kind=KIND_LIBM, base_probe="f_add_log", extended_probe="f_add_log_exp"),
    MachineCodePage(
        "exp2",
        kind=KIND_LIBM,
        base_probe="f_add_log2",
        extended_probe="f_add_log2_exp2",
        rationale=(
            "rule 2 · exp10-is-pow: `2 ** x` strength-reduces here because a standard-C port emits C99 `exp2`; "
            "the weight is measured on the "
            "real `exp2` call"
        ),
    ),
    MachineCodePage(
        "exp10",
        kind=KIND_LIBM,
        base_probe="f_add_log10",
        extended_probe="f_add_log10_exp10",
        rationale=(
            "rule 2 · exp10-is-pow: `10 ** x` cannot strength-reduce to an `exp10` call -- `exp10` is not standard C "
            "-- so a port emits "
            "`pow(10, x)`, and that is exactly what the weight measures"
        ),
    ),
    MachineCodePage("expm1", kind=KIND_LIBM, base_probe="f_add_log1p", extended_probe="f_add_log1p_expm1"),
    MachineCodePage("fmod", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_fmod", range_sensitive=True),
    MachineCodePage("gamma", kind=KIND_LIBM, base_probe="f_add_gammabase", extended_probe="f_add_gammabase_gamma"),
    MachineCodePage(
        "hypot",
        kind=KIND_LIBM,
        base_probe="f_add",
        extended_probe="f_add_hypot",
        rationale=(
            "rule 2 · measurement-fallbacks: the 2-argument base weight is the real libm call; the hand-rolled "
            "scaled probes only supply the per- "
            "extra-coordinate slope, validated against this base (within ~10%)"
        ),
    ),
    MachineCodePage("lgamma", kind=KIND_LIBM, base_probe="f_add_gammabase", extended_probe="f_add_gammabase_lgamma"),
    MachineCodePage("log", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_log"),
    MachineCodePage("log1p", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_log1p"),
    MachineCodePage("log2", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_log2"),
    MachineCodePage("log10", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_log10"),
    MachineCodePage("pow", kind=KIND_LIBM, base_probe="f_pow", extended_probe="f_pow_pow"),
    MachineCodePage(
        "remainder",
        kind=KIND_LIBM,
        base_probe="f_add",
        extended_probe="f_add_remainder",
        rationale=(
            "rule 2 · measurement-fallbacks: numba has no `math.remainder`, so the probe calls libm through a ctypes "
            "binding -- still the bare call "
            "CPython executes"
        ),
        range_sensitive=True,
    ),
    MachineCodePage("sin", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_sin", range_sensitive=True),
    MachineCodePage(
        "sinh", kind=KIND_LIBM, base_probe="f_add_asinh", extended_probe="f_add_asinh_sinh", range_sensitive=True
    ),
    MachineCodePage("tan", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_tan", range_sensitive=True),
    MachineCodePage("tanh", kind=KIND_LIBM, base_probe="f_add", extended_probe="f_add_tanh", range_sensitive=True),
    # --- arity-scaled algorithms -----------------
    MachineCodePage(
        "dist",
        kind=KIND_ARITY,
        base_probe="f_add",
        extended_probe="f_add_dist2",
        rationale=(
            "rule 2 · measurement-fallbacks: hand-rolled overflow-safe port (no libm `dist` exists); prices the "
            "scaled algorithm `math.dist` executes, "
            "not a naive sum of squares"
        ),
    ),
    MachineCodePage(
        "dist_xarg",
        kind=KIND_ARITY,
        base_probe="f_add_dist2",
        extended_probe="f_add_dist8",
        rationale="per-extra-coordinate slope of the same overflow-safe port as `DIST`",
        probe_span=6,
    ),
    MachineCodePage(
        "sumprod",
        kind=KIND_ARITY,
        base_probe="f_add",
        extended_probe="f_add_sumprod2",
        rationale=(
            "rule 2 · measurement-fallbacks: faithful port of CPython's extended-precision (TripleLength) "
            "accumulation, error terms emitted "
            "through the llvm.fma intrinsic; the 2-element base includes the close-out"
        ),
    ),
    MachineCodePage(
        "sumprod_xelem",
        kind=KIND_ARITY,
        base_probe="f_add_sumprod2",
        extended_probe="f_add_sumprod8",
        rationale="per-extra-element slope of the same TripleLength port as `SUMPROD`",
        probe_span=6,
    ),
    MachineCodePage(
        "hypot_xarg",
        kind=KIND_ARITY,
        base_probe="f_add_hypot_scaled2",
        extended_probe="f_add_hypot_scaled8",
        rationale=(
            "rule 2 · measurement-fallbacks: hand-rolled overflow-safe port (numba cannot compile n-ary `hypot`); "
            "deterministic per-coordinate cost, "
            "so rule 2 applies to the port"
        ),
        probe_span=6,
    ),
]


def best_matching_loops(base_loops: list[list[str]], extended_loops: list[list[str]]) -> tuple[list[str], list[str]]:
    """The pair of loops (one per probe) with the highest line-level similarity.

    When a probe compiles to several innermost loops (unrolled main + remainder), the remainder
    is the one structurally comparable to the other probe's loop -- highest-similarity selection
    finds it without hard-coding which probe unrolled.
    """
    _, base, extended = max(
        (difflib.SequenceMatcher(a=base, b=extended).ratio(), base, extended)
        for base in base_loops
        for extended in extended_loops
    )
    return base, extended


def render_diff_block(page: MachineCodePage, base: list[str], extended: list[str]) -> str:
    """The unified diff of the best-matching loop pair, as a `diff`-fenced markdown block."""
    body: list[str] = []
    for tag, a_lo, a_hi, b_lo, b_hi in difflib.SequenceMatcher(a=base, b=extended).get_opcodes():
        if tag in ("equal", "delete", "replace"):
            body.extend(f"  {line}" if tag == "equal" else f"- {line}" for line in base[a_lo:a_hi])
        if tag in ("insert", "replace"):
            body.extend(f"+ {line}" for line in extended[b_lo:b_hi])
    return "\n".join(["```diff", f"--- {page.base_probe}", f"+++ {page.extended_probe}", *body, "```"])


def render_structure_block(page: MachineCodePage, probes_by_name: dict[str, CompiledProbe]) -> str:
    """Each probe's innermost-loop inventory, with the full function ASM behind a collapsible.

    The inventory line is the at-a-glance unrolling check (one loop vs. main + remainder); the
    collapsed complete listings let a reader verify the diffed loop was not cherry-picked and
    that nothing relevant sits outside it.
    """
    inventory = [
        f"- `{name}` -- {len(compiled.loops)} innermost loop(s): "
        + ", ".join(f"{len(loop)} instructions" for loop in compiled.loops)
        for name, compiled in probes_by_name.items()
    ]
    intro = [
        "The listings below are the complete compiled functions the benchmark times, raw as numba",
        "emits them (the cpython call wrappers around them are omitted -- they never run inside the",
        "timed loop). Listing lengths reflect the compiler's unrolling choices, not the probes'",
        "amount of work -- see the discussion below.",
    ]
    listings: list[str] = []
    for name, compiled in probes_by_name.items():
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


def link_interpretation_citations(text: str) -> str:
    """Turn every `rule N · slug` citation in `text` into a link to that interpretation entry.

    Applied to the rationale column rather than written into each rationale, so the citation form
    stays the single thing an author has to get right and every entry becomes reachable in one
    click. The slugs are frozen, so the anchor a citation resolves to cannot drift.
    """
    return re.sub(
        r"(rule \d+ · )([a-z][a-z0-9-]*)",
        r"\1[\2](cost_model_interpretations.md#\2)",
        text,
    )


def render_cost_model_table() -> str:
    """The per-FlopType pricing table on the cost-model page, derived from the page registry.

    F2I and I2F close the table as static rows: they are the only FlopTypes without a benchmark
    probe (spec-sheet and third-party sources price them), so the registry cannot supply them.
    """
    rows = [
        "| Flop type | Weight measured as | Rule | Notes |",
        "|---|---|---|---|",
    ]
    for page in sorted(PAGES, key=lambda entry: entry.doc_name):
        name_cell = f"[`{page.doc_name.upper()}`](machine_code/{page.doc_name}.md)"
        difference = f"`{page.extended_probe}` − `{page.base_probe}`"
        measured_cell = difference if page.probe_span == 1 else f"({difference}) / {page.probe_span}"
        rule_cell = RULE_BY_KIND[page.kind] + (", 4" if page.range_sensitive else "")
        rows.append(
            f"| {name_cell} | {measured_cell} | {rule_cell} | {link_interpretation_citations(page.rationale)} |"
        )
    rows.append(
        "| `F2I` | *(no benchmark probe — priced from spec sheets and third-party tables)* | 1 | "
        "float→int conversion instruction of the port |"
    )
    rows.append(
        "| `I2F` | *(no benchmark probe — priced from spec sheets and third-party tables)* | 1 | "
        "int→float conversion instruction of the port |"
    )
    return "\n".join(rows)


def regenerate_pages() -> dict[Path, str]:
    """Regenerate every page's marked blocks; returns the intended full content per page file."""
    probe_cache: dict[str, CompiledProbe] = {}

    def compiled(probe_name: str) -> CompiledProbe:
        if probe_name not in probe_cache:
            probe_cache[probe_name] = compile_probe(probe_name)
        return probe_cache[probe_name]

    regenerated: dict[Path, str] = {}
    for page in PAGES:
        base_probe, extended_probe = compiled(page.base_probe), compiled(page.extended_probe)
        base, extended = best_matching_loops(base_probe.loops, extended_probe.loops)
        marker_stem = f"machine-code-{page.doc_name.replace('_', '-')}"
        replacements = {
            f"{marker_stem}-diff": render_diff_block(page, base, extended),
            f"{marker_stem}-structure": render_structure_block(
                page, {page.base_probe: base_probe, page.extended_probe: extended_probe}
            ),
        }
        file_path = MACHINE_CODE_DOCS_DIR / f"{page.doc_name}.md"
        regenerated[file_path] = rewrite_marked_blocks(read_lf(file_path), file_path, replacements)
    index_path = MACHINE_CODE_DOCS_DIR / "index.md"
    regenerated[index_path] = rewrite_marked_blocks(
        read_lf(index_path), index_path, {"machine-code-page-list": render_page_list_block()}
    )
    pricing_path = REPO_ROOT / "docs" / "cost_model_pricing.md"
    regenerated[pricing_path] = rewrite_marked_blocks(
        read_lf(pricing_path), pricing_path, {"cost-model-flop-type-table": render_cost_model_table()}
    )
    return regenerated


# ==================================================================================================
#  Entry point
# ==================================================================================================
def main() -> int:
    """Regenerate the machine-code listing blocks; `--check` verifies instead of writing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on stale listings, write nothing")
    args = parser.parse_args()

    if platform.machine() != REQUIRED_MACHINE:
        sys.stderr.write(
            f"the machine-code listings are committed as {REQUIRED_MACHINE}; "
            f"refusing to regenerate on '{platform.machine()}' -- see module docstring\n"
        )
        return 1

    regenerated = regenerate_pages()
    if args.check:
        stale = [path for path, intended in regenerated.items() if read_lf(path) != intended]
        for path in stale:
            sys.stderr.write(f"stale machine-code listings in {path.relative_to(REPO_ROOT)}\n")
        if stale:
            sys.stderr.write("run `make regen-machine-code`\n")
            return 1
        return 0

    for file_path, intended in regenerated.items():
        if read_lf(file_path) != intended:
            file_path.write_text(intended, encoding="utf-8", newline="\n")
            print(f"rewrote {file_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
