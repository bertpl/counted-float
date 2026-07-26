"""Emit the built-in flop-weight bar chart as a deterministic SVG.

Hand-emitted rather than plotted: a grouped bar chart is `<rect>` plus `<text>`, so this needs no
plotting dependency and — unlike a raster render — its bytes are reproducible, which lets the
committed file be checked by re-deriving and comparing rather than by hashing its inputs.

Determinism is a requirement, not a happy accident. Every coordinate is rounded before formatting
(`_n`), every float is formatted explicitly rather than through `repr`, and iteration order comes
from sorted sequences — never a set. Without that, a last-ULP difference in `math.log10` between
platforms would change the committed bytes and fail the drift check for no real reason.
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING

from builtin_data_sources import source_summary

from counted_float.config import get_builtin_flop_weights, get_default_consensus_flop_weights

if TYPE_CHECKING:
    from counted_float._core.models import FlopType

# --- series ------------------------------------
# True neutral grey for the all-architecture aggregate -- equal channels, no undertone -- so the two
# ISA series carry all of the color. Checked for colorblind separation: the worst adjacent pair sits
# around ΔE 25 under both protanopia and tritanopia, far above the ΔE 8 target.
#
# The blue is chroma-matched to the peach (both ~0.133 in OKLab) rather than lightness-matched, which
# is what makes the pair read as equally soft. Matching lightness instead is not available: sRGB blue
# cannot hold that chroma at the peach's lightness, and the pale blue it forces drops to half the
# chroma and to ΔE 18 separation.
#
# The peach sits above the perceptual lightness band, which costs it contrast against white (roughly
# 1.8:1) -- accepted deliberately, since the axis labels and legend carry identity anyway and a
# band-compliant peach read muddy next to the blue.
OVERALL_COLOR = "#707070"
ARM_COLOR = "#FBB85C"
X86_COLOR = "#6BA1F2"


# --- neutral ramps -----------------------------
# The series colors above hold up on either surface; only the neutrals have to change. So a theme is
# exactly one ramp, and the two committed charts differ in nothing else -- same data, same layout,
# same geometry, substituted inks. `Theme.surface` is opaque: the chart brings its own background so
# it stays legible even when the page theme and the reader's `prefers-color-scheme` disagree.
@dataclasses.dataclass(frozen=True)
class Theme:
    """One surface and the neutral inks that read against it.

    Attributes:
        name: Used in the committed file name.
        surface: The chart's own background, opaque so the chart stays legible on any page.
        legend_surface: The legend panel, one step off `surface` so it reads as a panel rather than
            as a hole in the grid.
        title_ink: The chart title.
        label_ink: Axis labels, category labels, legend text -- anything meant to be read.
        muted_ink: Secondary tick labels and the elision note.
        grid_ink: Minor (non-decade) gridlines.
        major_grid_ink: Decade gridlines.
        axis_ink: The category axis.
    """

    name: str
    surface: str
    legend_surface: str
    title_ink: str
    label_ink: str
    muted_ink: str
    grid_ink: str
    major_grid_ink: str
    axis_ink: str


LIGHT_THEME = Theme(
    name="light",
    surface="#FFFFFF",
    legend_surface="#F0F3F6",
    title_ink="#1F2328",
    label_ink="#57606A",
    muted_ink="#8C959F",
    grid_ink="#D0D7DE",
    major_grid_ink="#AFB8C1",
    axis_ink="#AFB8C1",
)
DARK_THEME = Theme(
    name="dark",
    surface="#0D1117",
    legend_surface="#242C37",
    title_ink="#E6EDF3",
    label_ink="#B1BAC4",
    muted_ink="#8B949E",
    grid_ink="#444C56",
    major_grid_ink="#636C76",
    axis_ink="#6E7681",
)
# mkdocs-material's slate surface, which is a different dark from GitHub's. Same ramp otherwise --
# only the two surfaces move, so the docs page gets a chart whose panel edge does not show.
DOCS_DARK_THEME = dataclasses.replace(DARK_THEME, name="dark_docs", surface="#1E2129", legend_surface="#333846")
THEMES = [LIGHT_THEME, DARK_THEME, DOCS_DARK_THEME]

LEGEND_BACKDROP_OPACITY = "0.8"
# More dash than gap: a long gap reads as dots at this line weight.
MINOR_DASH = "3 2"

# Legend metrics. The panel is derived from the text's own bounds rather than from the row count, so
# it stays centred on what it sits behind. SVG cannot measure text, so the label width is estimated
# from the longest label at `LEGEND_CHAR_W` per character -- approximate by necessity, and the only
# number here that is not exact.
LEGEND_ROW_H = 16
LEGEND_PAD = 6
LEGEND_FONT = 11
LEGEND_ASCENT = 8  # baseline to cap height, and also the swatch's rise above the baseline
LEGEND_SWATCH = 10
LEGEND_SWATCH_GAP = 6
LEGEND_CHAR_W = 5.35

# --- geometry ----------------------------------
# Width is *derived* from the bar layout rather than fixed: a wider break or a wider bar silently
# pushed the last group past a hardcoded right edge, where the viewBox clipped two bars away.
HEIGHT = 470
PLOT_LEFT = 46
RIGHT_MARGIN = 10
PLOT_TOP = 64
PLOT_BOTTOM = 366

# Provenance lives in a footnote rather than a third header line: the counts matter for trust, not for
# reading the bars, so they belong out of the way with a marker pointing at them from the title.
FOOTNOTE_MARKER = "1"
FOOTNOTE_BASELINE = HEIGHT - 12
# Tucked into the corner rather than aligned to the plot: it annotates the whole chart, not the axis.
FOOTNOTE_LEFT = 12
FOOTNOTE_MARKER_RISE = 3

BAR_W = 9  # three touching bars per flop type -- the group reads as one unit
GROUP_GAP = 9
# The omitted middle gets real width, and the category axis runs *dashed* across it -- a broken line
# says "the sequence continues" without planting a mark that could be misread as data.
BREAK_W = 64
BREAK_DASH_SPAN = 48

# How many flop types are shown at each end. The middle is elided: the point is the *range*, and
# every flop type times three bars would be unreadable at README width.
#
# The split is deliberately lopsided. The cheap end carries the information -- it is where the two
# ISAs actually disagree, and it stops just before the step up to REMAINDER, so the break lands on a
# real discontinuity rather than an arbitrary cutoff. The expensive end is a plateau: everything from
# rank 41 up sits within a few points of everything else, so extra bars there restate one fact.
N_CHEAPEST = 17
N_PRICIEST = 3

# --- scale -------------------------------------
# Log y, because the weights span well over two decades. Bounds are round numbers outside the data
# on both ends; `_check_within_axis` fails the build if the data ever grows past them, since a bar
# clipped to zero height disappears silently rather than looking wrong.
Y_MIN = 0.15
Y_MAX = 80.0
# Decades are the majors: solid line, normal-size label. 1 is also ADD, the unit everything else is
# relative to. Every integer multiple in between gets a dotted line so the log spacing is legible,
# but only the 2 and the 5 of each decade are labelled -- enough to read the scale without turning
# the plot into a ruler.
Y_MAJOR_TICKS = [1.0, 10.0]
Y_LABELLED_MULTIPLES = [2, 5]
_DECADES = [0.1, 1.0, 10.0]

_COORD_DECIMALS = 3


def _minor_ticks() -> list[tuple[float, bool]]:
    """Every in-range integer multiple within each decade, as (value, is labelled)."""
    ticks: list[tuple[float, bool]] = []
    for decade in _DECADES:
        for multiple in range(2, 10):
            value = round(decade * multiple, 6)
            if Y_MIN <= value <= Y_MAX:
                ticks.append((value, multiple in Y_LABELLED_MULTIPLES))
    return ticks


def _n(value: float) -> str:
    """Format one coordinate, rounded so platform float noise cannot reach the committed bytes.

    Three decimals is far below anything visible — at this viewBox one user unit is about two device
    pixels on a high-DPI display — and far above the last-ULP variation `math.log10` can differ by
    across platforms.
    """
    return f"{round(value, _COORD_DECIMALS):.3f}"


def _y(value: float) -> float:
    """Map a weight onto the log y axis, in user units from the top of the viewBox."""
    span = math.log10(Y_MAX) - math.log10(Y_MIN)
    frac = (math.log10(value) - math.log10(Y_MIN)) / span
    return PLOT_BOTTOM - frac * (PLOT_BOTTOM - PLOT_TOP)


def _omitted_count() -> int:
    """How many flop types the break stands for -- derived, so it cannot drift from the data."""
    total = len(get_default_consensus_flop_weights(rounding_mode=None).weights)
    return total - N_CHEAPEST - N_PRICIEST


def _check_within_axis(plotted: list[tuple[str, str, float]]) -> None:
    """Fail if any plotted weight falls outside the axis bounds.

    A value below `Y_MIN` renders as a zero-height bar — indistinguishable from a missing series
    rather than obviously wrong — so this is checked rather than trusted. Widen the bounds and add a
    tick when it fires.

    Args:
        plotted: (series name, flop type name, weight) for every bar the chart will draw.

    Raises:
        ValueError: If any weight lies outside `[Y_MIN, Y_MAX]`.
    """
    outside = [(series, name, value) for series, name, value in plotted if not Y_MIN <= value <= Y_MAX]
    if outside:
        detail = ", ".join(f"{series}/{name}={value:.4g}" for series, name, value in sorted(outside))
        raise ValueError(f"weights outside the chart's y axis [{Y_MIN}, {Y_MAX}]: {detail}")


def _shown_flop_types() -> tuple[list[FlopType], list[FlopType]]:
    """The cheapest and priciest flop types by overall weight, as (cheapest, priciest).

    Sorted by (weight, name) so two equal weights cannot reorder between runs.
    """
    overall = get_default_consensus_flop_weights(rounding_mode=None).weights
    ordered = sorted(overall, key=lambda flop_type: (overall[flop_type], flop_type.name))
    return ordered[:N_CHEAPEST], ordered[-N_PRICIEST:]


def build_svg(theme: Theme) -> str:
    """The full committed SVG for the built-in flop-weight chart, on one theme's surface.

    Args:
        theme: The neutral ramp and surface to draw against.
    """
    overall = get_default_consensus_flop_weights(rounding_mode=None).weights
    arm = get_builtin_flop_weights(key_filter="arm", rounding_mode=None).weights
    x86 = get_builtin_flop_weights(key_filter="x86", rounding_mode=None).weights
    cheapest, priciest = _shown_flop_types()
    provenance = source_summary()
    series_by_name = [("all", overall), ("arm64", arm), ("x86", x86)]
    _check_within_axis(
        [
            (series_name, flop_type.name, series[flop_type])
            for series_name, series in series_by_name
            for flop_type in [*cheapest, *priciest]
        ]
    )

    # --- layout ---------------------------------
    # Positions first, so the category axis can be drawn with a gap where the ellipsis goes, and so
    # the canvas can be sized to whatever the bars actually need.
    shown = [*cheapest, *priciest]
    group_w = 3 * BAR_W
    group_x: list[float] = []
    break_centre = 0.0
    x = float(PLOT_LEFT) + GROUP_GAP / 2
    for index in range(len(shown)):
        if index == N_CHEAPEST:
            break_centre = x + BREAK_W / 2 - GROUP_GAP / 2
            x += BREAK_W
        group_x.append(x)
        x += group_w + GROUP_GAP
    plot_right = group_x[-1] + group_w + GROUP_GAP / 2
    width = plot_right + RIGHT_MARGIN

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_n(width)} {HEIGHT}" '
        f'width="{_n(width)}" height="{HEIGHT}" font-family="system-ui, -apple-system, sans-serif">',
        f'<rect x="0" y="0" width="{_n(width)}" height="{HEIGHT}" fill="{theme.surface}"/>',
        # the superscript marker points at the footnote at the foot of the chart; `dy` rather than
        # `baseline-shift`, which renderers support unevenly
        f'<text x="{PLOT_LEFT}" y="26" font-size="15" font-weight="600" fill="{theme.title_ink}">'
        f'Built-in flop weights<tspan font-size="9" font-weight="400" dx="2" dy="-6" '
        f'fill="{theme.muted_ink}">({FOOTNOTE_MARKER})</tspan></text>',
        f'<text x="{PLOT_LEFT}" y="44" font-size="11" fill="{theme.label_ink}">relative to ADD = 1, log scale</text>',
    ]

    # --- gridlines and y labels -----------------
    for tick, labelled in _minor_ticks():
        y = _y(tick)
        out.append(
            f'<line x1="{PLOT_LEFT}" y1="{_n(y)}" x2="{_n(plot_right)}" y2="{_n(y)}" '
            f'stroke="{theme.grid_ink}" stroke-width="0.75" stroke-dasharray="{MINOR_DASH}"/>'
        )
        if labelled:
            out.append(
                f'<text x="{PLOT_LEFT - 8}" y="{_n(y + 3)}" font-size="8" fill="{theme.muted_ink}" '
                f'text-anchor="end">{tick:g}</text>'
            )
    for tick in Y_MAJOR_TICKS:
        y = _y(tick)
        out.append(
            f'<line x1="{PLOT_LEFT}" y1="{_n(y)}" x2="{_n(plot_right)}" y2="{_n(y)}" '
            f'stroke="{theme.major_grid_ink}" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{PLOT_LEFT - 8}" y="{_n(y + 3.5)}" font-size="10" fill="{theme.label_ink}" '
            f'text-anchor="end">{tick:g}</text>'
        )

    # --- category axis, dashed across the elision
    dash_left = break_centre - BREAK_DASH_SPAN / 2
    dash_right = break_centre + BREAK_DASH_SPAN / 2
    for x1, x2 in [(float(PLOT_LEFT), dash_left), (dash_right, plot_right)]:
        out.append(
            f'<line x1="{_n(x1)}" y1="{PLOT_BOTTOM}" x2="{_n(x2)}" y2="{PLOT_BOTTOM}" '
            f'stroke="{theme.axis_ink}" stroke-width="1"/>'
        )
    out.append(
        f'<line x1="{_n(dash_left)}" y1="{PLOT_BOTTOM}" x2="{_n(dash_right)}" y2="{PLOT_BOTTOM}" '
        f'stroke="{theme.axis_ink}" stroke-width="1" stroke-dasharray="4 4"/>'
    )
    out.append(
        f'<text x="{_n(break_centre)}" y="{PLOT_BOTTOM + 16}" font-size="8.5" '
        f'fill="{theme.muted_ink}" text-anchor="middle">{_omitted_count()} more</text>'
    )

    # --- bars -----------------------------------
    for flop_type, left in zip(shown, group_x, strict=True):
        for offset, (series, color) in enumerate([(overall, OVERALL_COLOR), (arm, ARM_COLOR), (x86, X86_COLOR)]):
            top = _y(series[flop_type])
            out.append(
                f'<rect x="{_n(left + offset * BAR_W)}" y="{_n(top)}" width="{BAR_W}" '
                f'height="{_n(PLOT_BOTTOM - top)}" fill="{color}"/>'
            )
        label_x = left + group_w / 2
        out.append(
            f'<text x="{_n(label_x)}" y="{PLOT_BOTTOM + 13}" font-size="9" fill="{theme.label_ink}" '
            f'text-anchor="end" transform="rotate(-45 {_n(label_x)} {PLOT_BOTTOM + 13})">'
            f"{flop_type.name}</text>"
        )

    # --- legend ---------------------------------
    # Sits over the plot, so it gets a translucent panel one step off the chart background: enough to
    # read as a panel and to fade the gridlines behind the text, without hiding them outright.
    rows = [("all architectures", OVERALL_COLOR), ("arm64", ARM_COLOR), ("x86", X86_COLOR)]
    legend_x = PLOT_LEFT + 12
    legend_y = PLOT_TOP + 16
    # Panel bounds come from the rows' own extent, so the padding is equal on every side. The swatches
    # are the tallest thing in a row and no label carries a descender, so a row's visual top and
    # bottom are the swatch's -- not a baseline plus an unused descent allowance.
    content_top = legend_y - LEGEND_ASCENT
    content_bottom = legend_y + (len(rows) - 1) * LEGEND_ROW_H + (LEGEND_SWATCH - LEGEND_ASCENT)
    text_w = max(len(label) for label, _ in rows) * LEGEND_CHAR_W
    out.append(
        f'<rect x="{_n(legend_x - LEGEND_PAD)}" y="{_n(content_top - LEGEND_PAD)}" '
        f'width="{_n(LEGEND_SWATCH + LEGEND_SWATCH_GAP + text_w + 2 * LEGEND_PAD)}" '
        f'height="{_n(content_bottom - content_top + 2 * LEGEND_PAD)}" '
        f'rx="4" fill="{theme.legend_surface}" fill-opacity="{LEGEND_BACKDROP_OPACITY}"/>'
    )
    for row, (label, color) in enumerate(rows):
        y = legend_y + row * LEGEND_ROW_H
        out.append(
            f'<rect x="{legend_x}" y="{_n(y - LEGEND_ASCENT)}" width="{LEGEND_SWATCH}" '
            f'height="{LEGEND_SWATCH}" rx="1" fill="{color}"/>'
        )
        out.append(
            f'<text x="{_n(legend_x + LEGEND_SWATCH + LEGEND_SWATCH_GAP)}" y="{_n(y)}" '
            f'font-size="{LEGEND_FONT}" fill="{theme.label_ink}">{label}</text>'
        )

    # --- footnote -------------------------------
    # The marker mirrors the one on the title -- raised and a step darker than the note itself, so it
    # reads as a reference rather than as the first word of the sentence.
    out.append(
        f'<text x="{FOOTNOTE_LEFT}" y="{FOOTNOTE_BASELINE}" font-size="9" fill="{theme.muted_ink}">'
        f'<tspan font-size="7.5" font-weight="600" dy="-{FOOTNOTE_MARKER_RISE}" '
        f'fill="{theme.label_ink}">({FOOTNOTE_MARKER})</tspan>'
        f'<tspan dx="3" dy="{FOOTNOTE_MARKER_RISE}">based on {provenance}</tspan></text>'
    )

    out.append("</svg>")
    return "\n".join(out) + "\n"
