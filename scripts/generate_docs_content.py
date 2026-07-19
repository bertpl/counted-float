"""Regenerate the dataset-derived content committed in README.md and docs/.

Run via `make regen-docs` whenever the built-in data, the weight aggregation, or the rendering
code changes. Two kinds of content are generated:

  - **marked text blocks** — regions of README.md and docs/*.md sitting between
    `<!-- BEGIN generated: <name> -->` and `<!-- END generated: <name> -->` markers. Only these
    regions are rewritten; surrounding prose is never touched. A test regenerates them and fails
    on any diff with the committed content, so forgetting to run this after a data change fails
    the suite rather than shipping stale docs (same shape as the precomputed-weights generator).
  - **images** — terminal screenshots (`show-data`, the verbosity examples), captured as ANSI
    from the real library output and rendered to WebP. Excluded from the drift test: they only
    regenerate byte-identically on the machine that produced them. Refreshed by this script as
    part of the same run, or skipped with `--text-only`.

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
import difflib
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from counted_float import BuiltInData
from counted_float._core.models import FlopType
from counted_float.config import (
    get_active_flop_weights,
    get_builtin_flop_weights,
    get_default_consensus_flop_weights,
)

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
SNIPPETS_DIR = Path(__file__).resolve().parent / "docs_snippets"
IMAGES_DIR = REPO_ROOT / "docs" / "images"

TERMSHOT_PINNED_VERSION = "0.6.1"

# Rendering geometry. The show-data capture is taken wide enough that show() emits one single
# column block (instead of wrapping into stacked blocks), then cropped to the leading columns.
SHOW_DATA_CAPTURE_COLUMNS = 460
SHOW_DATA_IMAGE_CROP_COLUMNS = 190
# The committed cli.md slice keeps the flop-type columns through I2F, matching the docs prose.
CLI_SLICE_LAST_COLUMN = "I2F"

_MARKER_RE = re.compile(r"<!-- (BEGIN|END) generated: ([a-z0-9-]+) -->")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# ==================================================================================================
#  ANSI helpers
# ==================================================================================================
def strip_ansi(text: str) -> str:
    """Remove all ANSI style sequences from `text`."""
    return _ANSI_RE.sub("", text)


def crop_ansi_line(line: str, width: int) -> str:
    """Crop one line to `width` *visible* columns, keeping every ANSI escape.

    Escapes count zero columns, so styling state stays balanced across the cut. A line that
    actually lost content gets a reset plus a dim ellipsis appended.
    """
    out: list[str] = []
    visible = 0
    pos = 0
    truncated = False
    for match in _ANSI_RE.finditer(line):
        for ch in line[pos : match.start()]:
            if visible >= width:
                truncated = True
                break
            out.append(ch)
            visible += 1
        out.append(match.group())
        pos = match.end()
    for ch in line[pos:]:
        if visible >= width:
            truncated = True
            break
        out.append(ch)
        visible += 1
    result = "".join(out)
    if truncated and line.strip():
        result += "\x1b[0m\x1b[2m …\x1b[0m"
    return result


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
        env=_capture_env(SHOW_DATA_CAPTURE_COLUMNS),
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
        env=_capture_env(100),
    )
    return result.stderr


def _capture_env(columns: int) -> dict[str, str]:
    """Environment that makes rich emit truecolor ANSI at a fixed width without a real TTY."""
    import os

    # PYTHONUTF8 keeps the child's stdout/stderr UTF-8 on Windows, whose default locale
    # encoding cannot represent the tree's box-drawing characters
    return os.environ | {
        "COLUMNS": str(columns),
        "FORCE_COLOR": "1",
        "COLORTERM": "truecolor",
        "PYTHONUTF8": "1",
    }


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


# Registry of every marked block: name -> (file containing it, generator producing its content).
# The rewriting engine checks the two directions against each other: a marker in a file with no
# generator here fails, and a generator whose marker is missing from its file fails too.
TEXT_BLOCKS: dict[str, tuple[Path, Callable[[], str]]] = {
    "source-counts": (REPO_ROOT / "README.md", generate_source_counts),
    "flop-weights-active": (REPO_ROOT / "docs" / "flop_weights.md", generate_flop_weights_active),
    "flop-weights-consensus-raw": (REPO_ROOT / "docs" / "flop_weights.md", generate_flop_weights_consensus_raw),
    "flop-weights-arm": (REPO_ROOT / "docs" / "flop_weights.md", generate_flop_weights_arm),
    "cli-show-data-slice": (REPO_ROOT / "docs" / "cli.md", generate_cli_show_data_slice),
    "builtin-data-table": (REPO_ROOT / "docs" / "builtin_data.md", generate_builtin_data_table),
    "snippet-verbosity-info": (REPO_ROOT / "docs" / "counting_flops.md", generate_snippet_verbosity_info),
    "snippet-verbosity-warning": (REPO_ROOT / "docs" / "counting_flops.md", generate_snippet_verbosity_warning),
    "snippet-verbosity-mixed": (REPO_ROOT / "docs" / "counting_flops.md", generate_snippet_verbosity_mixed),
}


# ==================================================================================================
#  Marked-block rewriting
# ==================================================================================================
def rewrite_marked_blocks(text: str, file_path: Path, replacements: dict[str, str]) -> str:
    """Replace every marked region in `text` with its regenerated content.

    Markers must be well-formed: BEGIN/END strictly alternating, names matching per pair, no
    nesting, every found name known, and every expected name found — anything else raises, so a
    malformed or half-deleted marker can never silently freeze a block.

    Args:
        text: The file's current content.
        file_path: Where the text came from, for error messages and registry validation.
        replacements: block name -> regenerated content (without the marker lines).

    Returns:
        The rewritten file content.
    """
    out: list[str] = []
    pos = 0
    open_name: str | None = None
    seen: set[str] = set()
    for match in _MARKER_RE.finditer(text):
        kind, name = match.groups()
        if kind == "BEGIN":
            if open_name is not None:
                raise ValueError(f"{file_path}: nested BEGIN marker '{name}' inside '{open_name}'")
            if name not in replacements:
                raise ValueError(f"{file_path}: marker '{name}' has no registered generator")
            if name in seen:
                raise ValueError(f"{file_path}: duplicate marker '{name}'")
            open_name = name
            seen.add(name)
            out.append(text[pos : match.end()])
            out.append("\n" + replacements[name] + "\n")
        else:
            if open_name is None:
                raise ValueError(f"{file_path}: END marker '{name}' without a BEGIN")
            if name != open_name:
                raise ValueError(f"{file_path}: END marker '{name}' closes BEGIN '{open_name}'")
            open_name = None
            out.append(match.group())
        pos = match.end()
    if open_name is not None:
        raise ValueError(f"{file_path}: BEGIN marker '{open_name}' is never closed")
    missing = set(replacements) - seen
    if missing:
        raise ValueError(f"{file_path}: expected markers not found: {sorted(missing)}")
    out.append(text[pos:])
    return "".join(out)


def regenerate_text_blocks() -> dict[Path, str]:
    """Regenerate all marked blocks; returns the intended full content per file."""
    by_file: dict[Path, dict[str, str]] = {}
    for name, (file_path, generator) in TEXT_BLOCKS.items():
        by_file.setdefault(file_path, {})[name] = generator()
    # CRLF-checkout normalization (Windows CI): blocks are generated with \n, so the
    # comparison and the rewrite both happen in \n space regardless of what git checked out
    return {
        file_path: rewrite_marked_blocks(_read_lf(file_path), file_path, replacements)
        for file_path, replacements in by_file.items()
    }


def _read_lf(file_path: Path) -> str:
    r"""Read a text file as UTF-8 with line endings normalized to \n."""
    return file_path.read_text(encoding="utf-8").replace("\r\n", "\n")


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
            [
                "termshot",
                "--raw-read",
                str(ansi_file),
                "-C",
                str(columns),
                "--no-decoration",
                "--no-shadow",
                "-f",
                str(raw_png),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "magick",
                str(raw_png),
                "-strip",
                "-resize",
                "40%",
                "-quality",
                "75",
                "-define",
                "webp:method=5",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )


def regenerate_show_data_image() -> Path:
    """Regenerate the show-data screenshot: full tree rows, leading columns, ellipsis-cropped."""
    ansi = capture_show_data_ansi()
    cropped = "\n".join(crop_ansi_line(line, SHOW_DATA_IMAGE_CROP_COLUMNS) for line in ansi.splitlines())
    out = IMAGES_DIR / "show_data.webp"
    render_ansi_to_image(cropped, SHOW_DATA_IMAGE_CROP_COLUMNS + 4, out)
    return out


def regenerate_verbosity_images() -> list[Path]:
    """Regenerate one output screenshot per verbosity docs snippet."""
    outputs: list[Path] = []
    for snippet in sorted(SNIPPETS_DIR.glob("verbosity_*.py")):
        ansi = capture_snippet_stderr_ansi(snippet)
        columns = max(len(strip_ansi(line)) for line in ansi.splitlines()) + 2
        out = IMAGES_DIR / f"{snippet.stem}.webp"
        render_ansi_to_image(ansi, columns, out)
        outputs.append(out)
    return outputs


# ==================================================================================================
#  Entry point
# ==================================================================================================
def main() -> int:
    """Regenerate docs content; `--check` verifies the text blocks instead of writing anything."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on stale text blocks, write nothing")
    parser.add_argument("--text-only", action="store_true", help="skip image regeneration")
    args = parser.parse_args()

    regenerated = regenerate_text_blocks()

    if args.check:
        stale = False
        for file_path, intended in regenerated.items():
            current = _read_lf(file_path)
            if current != intended:
                stale = True
                diff = difflib.unified_diff(
                    current.splitlines(),
                    intended.splitlines(),
                    lineterm="",
                    n=1,
                    fromfile=f"{file_path.name} (committed)",
                    tofile=f"{file_path.name} (regenerated)",
                )
                sys.stderr.write("\n".join(diff) + "\n")
        if stale:
            sys.stderr.write("stale generated docs content -- run `make regen-docs`\n")
            return 1
        return 0

    for file_path, intended in regenerated.items():
        if _read_lf(file_path) != intended:
            file_path.write_text(intended, encoding="utf-8", newline="\n")
            print(f"rewrote {file_path.relative_to(REPO_ROOT)}")

    if not args.text_only:
        _require_image_tools()
        for image in [regenerate_show_data_image(), *regenerate_verbosity_images()]:
            print(f"rendered {image.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
