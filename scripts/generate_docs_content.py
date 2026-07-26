"""Regenerate the dataset-derived content committed in README.md and docs/.

This module is the *content* half: which blocks and screenshots exist, and how each one is
produced. The kind-agnostic machinery underneath it — what a derived file is, and the single loop
that checks or rewrites a set of them — lives in the `docs_artifacts` package next door.

Run via `make regen-docs` whenever the built-in data, the weight aggregation, or the rendering
code changes. Three kinds of content are generated:

  - **marked text blocks** — regions of README.md and docs/*.md sitting between
    `<!-- BEGIN generated: <name> -->` and `<!-- END generated: <name> -->` markers. Only these
    regions are rewritten; surrounding prose is never touched. A test regenerates them and fails
    on any diff with the committed content, so forgetting to run this after a data change fails
    the suite rather than shipping stale docs (same shape as the precomputed-weights generator).
  - **terminal captures** — the raw ANSI each screenshot is rendered from, committed under
    `scripts/docs_captures/` and checked exactly like the text blocks. This is what puts the
    images under drift control: an image is a pure function of its capture plus the pinned
    rendering tools, and the capture is plain library output with no renderer involved, so it
    stays comparable on any machine. Committing it also makes an image change reviewable — a
    WebP is opaque in a diff, its capture is not.
  - **images** — the WebP screenshots (`show-data`, the verbosity examples), rendered from
    exactly the capture text committed next to them. Not compared byte-wise, since that would
    only ever hold on the machine that rendered them. Refreshed by this script as part of the
    same run, or skipped with `--text-only`.

Image tooling (regen machine only, never a runtime or CI dependency):
  - `termshot` (pinned: 0.6.1) renders a raw ANSI capture to PNG.
  - ImageMagick's `magick` downscales the render and encodes it as lossy WebP (q75), which
    cuts the committed file size by ~10x at no practical legibility cost.

The verbosity example snippets under `scripts/docs_snippets/` are the single source for both the
docs' input code blocks (embedded as marked text blocks) and the captured output images, so the
code shown and the output shown can never disagree.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import io
import shutil
import subprocess
import sys
import tempfile
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from docs_artifacts import (
    DocsArtifactManager,
    GeneratedFile,
    MarkedBlock,
    RenderedFile,
    capture_env,
    crop_ansi_line,
    marked_block_files,
    read_lf,
    strip_ansi,
)

from counted_float import BuiltInData
from counted_float._core.counting._math_patching import (
    _MATH_NOT_PATCHED,
    _NOT_PATCHED_DUNDER,
    _NOT_PATCHED_PREDICATE,
    _PATCHES,
    _UNCOUNTED_MATH,
)
from counted_float._core.models import FlopType
from counted_float.config import (
    get_active_flop_weights,
    get_builtin_flop_weights,
    get_default_consensus_flop_weights,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from docs_artifacts import DerivedFile

REPO_ROOT = Path(__file__).resolve().parent.parent
SNIPPETS_DIR = Path(__file__).resolve().parent / "docs_snippets"
CAPTURES_DIR = Path(__file__).resolve().parent / "docs_captures"
IMAGES_DIR = REPO_ROOT / "docs" / "images"
# Build metadata rather than documentation, so it sits with the generator that writes it instead of
# in docs/, where it would ship into the published site.
IMAGE_MANIFEST = Path(__file__).resolve().parent / "image_manifest.json"

TERMSHOT_PINNED_VERSION = "0.6.1"

# The two render stages' parameters, named once and used both to build an image and to fingerprint
# it -- so changing a parameter invalidates every image it affects, with nothing to remember to bump.
TERMSHOT_FLAGS = ["--no-decoration", "--no-shadow"]
MAGICK_FLAGS = ["-strip", "-resize", "40%", "-quality", "75", "-define", "webp:method=5"]
# Bump when the *shape* of the pipeline changes -- a stage added, reordered, or swapped for another
# tool. Parameter values need no bump: they are hashed above.
RENDER_RECIPE_VERSION = "1"

# Terminal captures are byte-exact ANSI, which is comparable across POSIX platforms but not against
# Windows: rich decides its color support there through the Windows console API rather than the
# COLORTERM / FORCE_COLOR environment this script sets, so the same output carries different escape
# sequences. Windows therefore neither checks nor rewrites the captures -- rewriting would ping-pong
# the committed bytes against every other platform. Nothing is lost in coverage: the *visible* text
# is what drifts with the data, and it is checked everywhere through the text blocks (the show-data
# docs slice is that same capture with its escapes stripped).
CAPTURES_ARE_COMPARABLE = sys.platform != "win32"

# Rendering geometry. The show-data capture is taken wide enough that show() emits one single
# column block (instead of wrapping into stacked blocks), then cropped to the leading columns.
SHOW_DATA_CAPTURE_COLUMNS = 600
SHOW_DATA_IMAGE_CROP_COLUMNS = 190
# The committed cli.md slice keeps the flop-type columns through I2F, matching the docs prose.
CLI_SLICE_LAST_COLUMN = "I2F"


@dataclasses.dataclass(frozen=True)
class Screenshot:
    """One committed screenshot: the terminal capture behind it, and how wide to render it.

    Attributes:
        capture: Produces the raw ANSI, exactly as committed and as rendered.
        render_columns: Terminal width to render that ANSI at, derived from the capture itself so
            the two cannot fall out of step.
    """

    capture: Callable[[], str]
    render_columns: Callable[[str], int]


# ==================================================================================================
#  Captures of live library output
# ==================================================================================================
def capture_show(show_call: Callable[[], None]) -> str:
    """Run a `.show()`-style callable and return what it printed to stdout."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        show_call()
    return buffer.getvalue().rstrip("\n")


def capture_show_data_ansi() -> str:
    """Run `counted_float show-data` wide enough for a single column block; return raw ANSI.

    Runs in a subprocess so the COLUMNS/color environment shapes rich's auto-detection exactly as
    it would a real terminal.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.argv = ['counted_float', 'show-data']; "
            "from counted_float._core._cli_main import main; main()",
        ],
        capture_output=True,
        encoding="utf-8",
        check=True,
        env=capture_env(SHOW_DATA_CAPTURE_COLUMNS),
    )
    return result.stdout


def capture_snippet_stderr_ansi(snippet: Path) -> str:
    """Run one docs snippet and return its colored stderr (where verbosity output goes)."""
    result = subprocess.run(
        [sys.executable, str(snippet)],
        capture_output=True,
        encoding="utf-8",
        check=True,
        cwd=snippet.parent,  # so the logged locations show the bare snippet file name
        env=capture_env(100),
    )
    return result.stderr


# ==================================================================================================
#  Text-block generators
# ==================================================================================================
def _classified_source_keys() -> tuple[list[str], list[str], list[str]]:
    """Split the built-in data keys into (benchmarks, spec sheets, third-party analyses)."""
    benchmarks: list[str] = []
    specs: list[str] = []
    third_party: list[str] = []
    for key in BuiltInData.get_flop_weights_dict():
        source_type, entry = key.split(".")[-2], key.split(".")[-1]
        if source_type == "benchmarks":
            benchmarks.append(key)
        elif source_type == "specs" or entry.startswith("specs"):
            specs.append(key)
        elif entry.startswith("analysis_"):
            third_party.append(key)
        else:
            raise ValueError(f"cannot classify built-in data key: {key}")
    return benchmarks, specs, third_party


def generate_source_counts() -> str:
    """The README bullet stating how many sources of each type back the shipped weights."""
    benchmarks, specs, third_party = _classified_source_keys()
    return (
        f"- {len(benchmarks)} benchmarks, {len(specs)} spec sheets, "
        f"{len(third_party)} third party measurements (Agner Fog, uops.info)"
    )


def _show_block(import_line: str, call_line: str, show_call: Callable[[], None]) -> str:
    """A fenced docs block: the interactive-style invocation plus its captured real output."""
    return f"```python\n{import_line}\n\n>>> {call_line}\n\n{capture_show(show_call)}\n```"


def generate_flop_weights_active() -> str:
    """The `get_active_flop_weights().show()` example block."""
    return _show_block(
        ">>> from counted_float.config import get_active_flop_weights",
        "get_active_flop_weights().show()",
        lambda: get_active_flop_weights().show(),
    )


def generate_flop_weights_consensus_raw() -> str:
    """The unrounded default-consensus example block."""
    return _show_block(
        "from counted_float.config import get_default_consensus_flop_weights",
        "get_default_consensus_flop_weights(rounding_mode=None).show()",
        lambda: get_default_consensus_flop_weights(rounding_mode=None).show(),
    )


def generate_flop_weights_arm() -> str:
    """The arm-filtered aggregation example block."""
    return _show_block(
        "from counted_float.config import get_builtin_flop_weights",
        'get_builtin_flop_weights(key_filter="arm").show()',
        lambda: get_builtin_flop_weights(key_filter="arm").show(),
    )


def generate_cli_show_data_slice() -> str:
    """The abbreviated `show-data` slice in the CLI docs: ARM subtree rows, leading columns.

    Derived from the same single-block capture the image uses. Rows run through the first
    `└─specs` aggregate (the end of the v8_x subtree); columns run through `CLI_SLICE_LAST_COLUMN`,
    each cut line marked with an ellipsis; an omission footer states what was cut.
    """
    lines = [line.rstrip() for line in strip_ansi(capture_show_data_ansi()).splitlines()]
    legend = lines[0]
    crop_width = legend.index(CLI_SLICE_LAST_COLUMN) + len(CLI_SLICE_LAST_COLUMN)
    n_columns_shown = len(legend[:crop_width].split())

    kept: list[str] = []
    for line in lines:
        kept.append(line[:crop_width] + ("  …" if len(line) > crop_width else ""))
        if "└─specs" in line:
            break
    body = "\n".join(kept)
    n_columns_omitted = len(FlopType) - n_columns_shown
    footer = (
        f"         ⋮   (remaining ARM specs, the full x86 subtree, "
        f"and {n_columns_omitted} more flop-type columns omitted)"
    )
    return f"```\n[~] counted_float show-data\n{body}\n{footer}\n```"


def generate_builtin_data_table() -> str:
    """The entries table in the built-in-data docs, derived from the data keys."""
    # group keys as {(isa, family): {source_type: [entry, ...]}}, preserving data order
    grouped: dict[tuple[str, str], dict[str, list[str]]] = {}
    for key in BuiltInData.get_flop_weights_dict():
        parts = key.split(".")
        isa, family, source_type, entry = parts[0], ".".join(parts[1:-2]), parts[-2], parts[-1]
        grouped.setdefault((isa, family), {}).setdefault(source_type, []).append(entry)

    source_type_order = ["benchmarks", "specs", "other"]
    rows = ["| ISA | µarch family | Entries |", "|---|---|---|"]
    for (isa, family), by_type in sorted(grouped.items()):
        cells = []
        for source_type in source_type_order:
            if source_type in by_type:
                names = ", ".join(f"`{entry}`" for entry in sorted(by_type[source_type]))
                cells.append(f"{source_type}: {names}")
        unknown = set(by_type) - set(source_type_order)
        if unknown:
            raise ValueError(f"unrecognized source type(s) {sorted(unknown)} under {isa}.{family}")
        rows.append(f"| {isa} | `{family}` | {' — '.join(cells)} |")
    return "\n".join(rows)


# --------------------------------------------------------------------------
#  math-coverage table
# --------------------------------------------------------------------------
# Membership comes from the patch tables in the library; what follows is only how each function is
# presented and in what order.  Every currently patched function must appear in one of the two
# instrumented buckets, so patching something new breaks this generator until its row is decided --
# which is what keeps the table from drifting behind the code.
#
# The two arity-parametric and two version-gated entries carry a note; the rest render bare.
_MATH_INSTRUMENTED_ORDER = [
    "sqrt", "cbrt", "exp", "exp2", "expm1", "log", "log2", "log10", "log1p", "pow",
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh",
    "asinh", "acosh", "atanh", "hypot", "dist", "fmod", "remainder", "gamma", "lgamma",
    "erf", "erfc", "fabs", "copysign", "fma", "sumprod",
]  # fmt: skip
_MATH_INSTRUMENTED_NOTES = {
    "hypot": "(+ `HYPOT_XARG` per coordinate beyond the second)",
    "dist": "(+ `DIST_XARG` likewise)",
    "fma": "(Python 3.13+)",
    "sumprod": (
        "(Python 3.12+; + `SUMPROD_XELEM` per element beyond the second — counted inputs are "
        "unboxed so the extended-precision algorithm runs)"
    ),
}
# patched, but presented by the decomposition each one counts rather than by a FlopType of its own.
# 1-argument `hypot` also belongs to this row's prose; `hypot` itself is presented above.
_MATH_DECOMPOSED = ["degrees", "radians", "prod", "fsum"]
_MATH_DECOMPOSED_CELL = (
    "`degrees` / `radians` → MUL; `prod` → one MUL per chained multiply; `fsum` → (n−1) ADD; 1-argument `hypot` → ABS"
)
# registered conditionally by the patch table, so they are absent from it on an older interpreter
# while still belonging in the committed table -- the note on each says from which version
_MATH_VERSION_GATED = {"fma", "sumprod"}
# uncounted, but shaped like a predicate, so the docs group it with them rather than with the
# float-representation helpers -- while saying that it alone performs real arithmetic
_MATH_UNCOUNTED_SHOWN_WITH_PREDICATES = {"isclose"}


def _math_names_by_reason(reason: str) -> list[str]:
    """The unpatched `math` functions sharing one stated reason, in table order."""
    return [name for name, entry_reason in _MATH_NOT_PATCHED.items() if entry_reason == reason]


def generate_math_coverage_table() -> str:
    """The `math`-coverage table in the patching docs, derived from the classification tables."""
    presented_as_instrumented = set(_MATH_INSTRUMENTED_ORDER) | set(_MATH_DECOMPOSED)
    if unpresented := set(_PATCHES) - presented_as_instrumented:
        raise ValueError(f"patched but missing from the coverage table: {sorted(unpresented)}")
    if fictional := presented_as_instrumented - set(_PATCHES) - _MATH_VERSION_GATED:
        raise ValueError(f"presented as patched but not in the patch table: {sorted(fictional)}")

    instrumented = ", ".join(
        f"`{name}`" + (f" {note}" if (note := _MATH_INSTRUMENTED_NOTES.get(name)) else "")
        for name in _MATH_INSTRUMENTED_ORDER
    )
    dunder = _math_names_by_reason(_NOT_PATCHED_DUNDER)
    helpers = [name for name in _UNCOUNTED_MATH if name not in _MATH_UNCOUNTED_SHOWN_WITH_PREDICATES]
    predicates = _math_names_by_reason(_NOT_PATCHED_PREDICATE) + sorted(_MATH_UNCOUNTED_SHOWN_WITH_PREDICATES)

    rows = [
        ("**Instrumented** (patched, counts its FlopType)", instrumented),
        (
            "**Instrumented, counted as a decomposition** (patched, counts the flops a compiled port would execute)",
            _MATH_DECOMPOSED_CELL,
        ),
        (
            "**Counted via dunder** (no patch needed — do not expect these in the patch list)",
            " / ".join(f"`math.{name}`" for name in dunder)
            + " → F2I through "
            + "/".join(f"`__{name}__`" for name in dunder)
            + "; the builtins `abs()` → ABS and `round()` → RND/F2I likewise count through their dunders",
        ),
        (
            "**Not instrumented** (returns a plain, uncounted `float`)",
            "exactly the float-representation helpers — " + ", ".join(f"`{name}`" for name in helpers),
        ),
        (
            "**Predicates** (uncounted, return a `bool`)",
            ", ".join(f"`{name}`" for name in predicates)
            + " — and truthiness (`bool(x)`, `if x:`, `assert x`), which a compiled port would test"
            " against zero. It is left uncounted because it appears constantly in ordinary control"
            " flow rather than in the arithmetic being measured; an *algorithmic* zero-test can be"
            " written `x != 0.0`, which counts `COMP`",
        ),
    ]
    return "\n".join(["| Coverage | Functions |", "|---|---|", *(f"| {left} | {right} |" for left, right in rows)])


def _snippet_source(name: str) -> str:
    """The committed snippet's source, as the docs' input code block."""
    return f"```python\n{(SNIPPETS_DIR / name).read_text(encoding='utf-8').rstrip()}\n```"


def generate_snippet_verbosity_info() -> str:
    """The INFO example's input code, embedded from its snippet file."""
    return _snippet_source("verbosity_info.py")


def generate_snippet_verbosity_warning() -> str:
    """The WARNING example's input code, embedded from its snippet file."""
    return _snippet_source("verbosity_warning.py")


def generate_snippet_verbosity_mixed() -> str:
    """The mixed INFO+WARNING example's input code, embedded from its snippet file."""
    return _snippet_source("verbosity_mixed.py")


# Registry of every marked block, by marker name. The rewriting engine checks the two directions
# against each other: a marker in a file with no generator here fails, and a generator whose marker
# is missing from its file fails too.
MARKED_BLOCKS: dict[str, MarkedBlock] = {
    "source-counts": MarkedBlock(REPO_ROOT / "README.md", generate_source_counts),
    "flop-weights-active": MarkedBlock(REPO_ROOT / "docs" / "flop_weights.md", generate_flop_weights_active),
    "flop-weights-consensus-raw": MarkedBlock(
        REPO_ROOT / "docs" / "flop_weights.md", generate_flop_weights_consensus_raw
    ),
    "flop-weights-arm": MarkedBlock(REPO_ROOT / "docs" / "flop_weights.md", generate_flop_weights_arm),
    "cli-show-data-slice": MarkedBlock(REPO_ROOT / "docs" / "cli.md", generate_cli_show_data_slice),
    "builtin-data-table": MarkedBlock(REPO_ROOT / "docs" / "builtin_data.md", generate_builtin_data_table),
    "math-coverage-table": MarkedBlock(REPO_ROOT / "docs" / "math_patching.md", generate_math_coverage_table),
    "snippet-verbosity-info": MarkedBlock(REPO_ROOT / "docs" / "counting_flops.md", generate_snippet_verbosity_info),
    "snippet-verbosity-warning": MarkedBlock(
        REPO_ROOT / "docs" / "counting_flops.md", generate_snippet_verbosity_warning
    ),
    "snippet-verbosity-mixed": MarkedBlock(REPO_ROOT / "docs" / "counting_flops.md", generate_snippet_verbosity_mixed),
}


# ==================================================================================================
#  Image generators
# ==================================================================================================
def _require_image_tools() -> None:
    """Fail with an actionable message when the regen machine lacks the image tooling."""
    for tool, hint in [("termshot", f"pinned {TERMSHOT_PINNED_VERSION}"), ("magick", "ImageMagick")]:
        if shutil.which(tool) is None:
            raise RuntimeError(f"'{tool}' ({hint}) is required to regenerate images -- see module docstring")


def render_ansi_to_image(ansi_text: str, columns: int, out_path: Path) -> None:
    """Render an ANSI capture to a committed WebP: termshot render, then downscale + encode.

    The 40% downscale of termshot's ~2x-scale glyphs keeps text legible while the lossy WebP
    encoding keeps the committed file small.
    """
    with tempfile.TemporaryDirectory() as tmp:
        ansi_file = Path(tmp) / "capture.ansi"
        raw_png = Path(tmp) / "raw.png"
        ansi_file.write_text(ansi_text, encoding="utf-8")
        subprocess.run(
            ["termshot", "--raw-read", str(ansi_file), "-C", str(columns), *TERMSHOT_FLAGS, "-f", str(raw_png)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["magick", str(raw_png), *MAGICK_FLAGS, str(out_path)],
            check=True,
            capture_output=True,
        )


def _capture_show_data_cropped() -> str:
    """The show-data capture as rendered: full tree rows, leading columns, ellipsis-cropped."""
    ansi = capture_show_data_ansi()
    return "\n".join(crop_ansi_line(line, SHOW_DATA_IMAGE_CROP_COLUMNS) for line in ansi.splitlines())


def _widest_visible_line(ansi_text: str) -> int:
    """Render width for a capture whose lines set their own: the longest one, plus a margin."""
    return max(len(strip_ansi(line)) for line in ansi_text.splitlines()) + 2


def _cropped_render_width(_ansi_text: str) -> int:
    """Render width for the show-data capture: its crop width plus a margin.

    Fixed rather than measured, because the capture was already cropped to exactly that width —
    the argument is what the sibling widths need, not what this one uses.
    """
    return SHOW_DATA_IMAGE_CROP_COLUMNS + 4


# Every committed screenshot, by name: how its terminal capture is produced, and how wide to render
# it. The captures themselves are committed text (see CAPTURES_DIR) and drift-tested; the images are
# rendered from exactly that text, so checking the capture is what keeps the images honest.
SCREENSHOTS: dict[str, Screenshot] = {
    "show_data": Screenshot(_capture_show_data_cropped, _cropped_render_width),
} | {
    snippet.stem: Screenshot(partial(capture_snippet_stderr_ansi, snippet), _widest_visible_line)
    for snippet in sorted(SNIPPETS_DIR.glob("verbosity_*.py"))
}


def capture_files() -> list[GeneratedFile]:
    """Each screenshot's terminal capture, as a committed file the driver can check.

    Pure text and free of any rendering tool, so these are part of the checked (and CI-verified)
    content rather than of the image step. Their raw ANSI is unreadable in a diff, hence
    `as_readable`.
    """
    return [
        GeneratedFile(
            path=CAPTURES_DIR / f"{name}.ansi",
            produce=screenshot.capture,
            producible_here=CAPTURES_ARE_COMPARABLE,
            as_readable=strip_ansi,
        )
        for name, screenshot in SCREENSHOTS.items()
    ]


def screenshot_images() -> list[RenderedFile]:
    """Each committed screenshot, as an artifact checked against a hash of what it is built from.

    A WebP cannot be byte-compared: `termshot` and `magick` are absent in CI, and their output
    differs by tool version anyway. So each one declares its inputs instead — which is every
    argument `render_ansi_to_image` receives plus the tool parameters it applies.
    """
    return [
        RenderedFile(path=IMAGES_DIR / f"{name}.webp", inputs=partial(_screenshot_render_inputs, name))
        for name in SCREENSHOTS
    ]


def _screenshot_render_inputs(name: str) -> list[str]:
    """Everything one screenshot's bytes are a function of, in a fixed order.

    The capture is read from disk rather than re-captured: it is fed to `termshot` verbatim, and it
    is itself byte-checked as a `GeneratedFile`, so a stale capture is caught as a stale capture
    rather than showing up here as a stale image. Reading it also keeps this computable on a machine
    that cannot produce captures at all.
    """
    ansi = read_lf(CAPTURES_DIR / f"{name}.ansi")
    return [
        ansi,
        str(SCREENSHOTS[name].render_columns(ansi)),
        TERMSHOT_PINNED_VERSION,
        *TERMSHOT_FLAGS,
        *MAGICK_FLAGS,
        RENDER_RECIPE_VERSION,
    ]


def render_images(captures: dict[Path, str]) -> list[Path]:
    """Render each capture to its committed screenshot.

    Args:
        captures: The freshly generated capture content, keyed by capture file path — the images
            are rendered from this rather than re-captured, so an image can never disagree with
            the capture committed next to it.

    Returns:
        The written image paths.
    """
    _require_image_tools()
    written: list[Path] = []
    for capture_path, ansi in captures.items():
        name = capture_path.stem
        out = IMAGES_DIR / f"{name}.webp"
        render_ansi_to_image(ansi, SCREENSHOTS[name].render_columns(ansi), out)
        written.append(out)
    return written


# ==================================================================================================
#  Entry point
# ==================================================================================================
def derived_files() -> list[DerivedFile]:
    """Every committed file this script owns: marked blocks, then captures, then screenshots."""
    return [*marked_block_files(MARKED_BLOCKS), *capture_files(), *screenshot_images()]


def main() -> int:
    """Regenerate docs content; `--check` verifies it instead of writing anything."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on stale generated content, write nothing")
    parser.add_argument("--text-only", action="store_true", help="skip rendering the images")
    args = parser.parse_args()

    capture_paths = {artifact.path for artifact in capture_files()}
    manager = DocsArtifactManager(derived_files(), root=REPO_ROOT, manifest_path=IMAGE_MANIFEST)

    if args.check:
        if stale := manager.check():
            sys.stderr.write(manager.stale_report(stale))
            return 1
        return 0

    regenerated = manager.regenerate()
    for file_path in regenerated.written:
        print(f"rewrote {file_path.relative_to(REPO_ROOT)}")

    if not CAPTURES_ARE_COMPARABLE:
        print("captures and screenshots skipped on this platform -- see CAPTURES_ARE_COMPARABLE")
        return 0
    if args.text_only:
        if any(file_path in capture_paths for file_path in regenerated.written):
            # the images are rendered from the captures, so stale-vs-capture is now possible
            print("captures changed -- re-run without --text-only to refresh the screenshots")
        return 0

    captures = {path: content for path, content in regenerated.intended.items() if path in capture_paths}
    for image in render_images(captures):
        print(f"rendered {image.relative_to(REPO_ROOT)}")

    # recorded last, so the manifest describes the images that were just written
    manager.record_fingerprints()
    print(f"recorded {IMAGE_MANIFEST.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
