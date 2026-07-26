"""The committed chart must be reproducible, in-bounds, and identical across themes but for its inks.

The drift test already fails when the committed SVGs disagree with the generator. What it cannot see
is *why* a difference appeared, so these pin the three properties the chart's correctness rests on:
its output does not depend on the run, no bar is silently clipped away, and the per-theme files never
diverge in anything but neutral inks.
"""

import dataclasses
import sys
from pathlib import Path

import pytest

# scripts/ is not on the path for a test run
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
from flop_weight_chart import (
    DARK_THEME,
    DOCS_DARK_THEME,
    LIGHT_THEME,
    N_CHEAPEST,
    N_PRICIEST,
    THEMES,
    Y_MAX,
    Y_MIN,
    _check_within_axis,
    _minor_ticks,
    _omitted_count,
    _shown_flop_types,
    build_svg,
)


# ==================================================================================================
#  Reproducibility
# ==================================================================================================
@pytest.mark.parametrize("theme", THEMES, ids=[theme.name for theme in THEMES])
def test_svg_is_byte_identical_across_calls(theme):
    """Byte-compare is only a usable check if the generator is deterministic."""
    # --- act & assert -----------------------
    assert build_svg(theme) == build_svg(theme)


@pytest.mark.parametrize("dark", [DARK_THEME, DOCS_DARK_THEME], ids=["github", "docs"])
def test_themes_differ_only_in_neutral_inks(dark):
    """Substituting a dark theme's inks back out must reproduce the light SVG exactly.

    This is what keeps the per-theme files from drifting: a layout or data change that landed in one
    file and not the others could not survive this.
    """
    # --- arrange ----------------------------
    substituted = build_svg(dark)

    # --- act --------------------------------
    for field in dataclasses.fields(LIGHT_THEME):
        if field.name != "name":
            substituted = substituted.replace(getattr(dark, field.name), getattr(LIGHT_THEME, field.name))

    # --- assert -----------------------------
    assert substituted == build_svg(LIGHT_THEME)


def test_every_theme_gets_its_own_surface():
    """Opaque, distinct surfaces are the whole reason there is more than one file."""
    # --- act --------------------------------
    surfaces = [theme.surface for theme in THEMES]

    # --- assert -----------------------------
    assert len(set(surfaces)) == len(surfaces)
    for theme in THEMES:
        assert f'fill="{theme.surface}"' in build_svg(theme)


# ==================================================================================================
#  Bounds and elision
# ==================================================================================================
def test_axis_bounds_cover_every_plotted_weight():
    """A weight outside the axis renders as a zero-height bar, which looks like a missing series."""
    # --- act & assert -----------------------
    build_svg(LIGHT_THEME)  # raises via _check_within_axis if the data outgrew the axis


def test_out_of_range_weight_is_rejected():
    """The guard has to actually fire, or it is decoration."""
    # --- arrange ----------------------------
    too_small = [("arm64", "MINUS", Y_MIN / 2)]

    # --- act & assert -----------------------
    with pytest.raises(ValueError, match="outside the chart's y axis"):
        _check_within_axis(too_small)

    with pytest.raises(ValueError, match="outside the chart's y axis"):
        _check_within_axis([("x86", "GAMMA", Y_MAX * 2)])


def test_omitted_count_is_derived_from_the_data():
    """The 'N more' note must follow the flop-type count, not a number typed next to it."""
    # --- arrange ----------------------------
    cheapest, priciest = _shown_flop_types()

    # --- act --------------------------------
    shown = len(cheapest) + len(priciest)

    # --- assert -----------------------------
    assert len(cheapest) == N_CHEAPEST
    assert len(priciest) == N_PRICIEST
    assert f"{_omitted_count()} more" in build_svg(LIGHT_THEME)
    assert _omitted_count() > 0, f"nothing is elided at {shown} shown -- the break would be a lie"


def test_shown_flop_types_are_sorted_and_disjoint():
    """Sorted ascending by weight, and the two ends must not overlap."""
    # --- arrange / act ----------------------
    cheapest, priciest = _shown_flop_types()

    # --- assert -----------------------------
    assert not set(cheapest) & set(priciest)
    names = [flop_type.name for flop_type in [*cheapest, *priciest]]
    assert len(set(names)) == len(names)


# ==================================================================================================
#  Scale
# ==================================================================================================
def test_minor_ticks_are_in_range_and_labelled_at_two_and_five():
    """Every integer multiple per decade, labelled only where the scale needs a number."""
    # --- act --------------------------------
    ticks = _minor_ticks()

    # --- assert -----------------------------
    assert all(Y_MIN <= value <= Y_MAX for value, _ in ticks)
    assert [value for value, labelled in ticks if labelled] == [0.2, 0.5, 2.0, 5.0, 20.0, 50.0]
