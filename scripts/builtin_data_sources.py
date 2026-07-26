"""How the built-in weight data breaks down by kind of source.

A fact about the dataset rather than about any one piece of documentation, and two generators need it
-- the README's source-count bullet and the chart's provenance subtitle. It lives here so neither has
to import the other, and so the two can never disagree about how many of each there are.
"""

from __future__ import annotations

import dataclasses

from counted_float import BuiltInData


@dataclasses.dataclass(frozen=True)
class SourceCounts:
    """How many built-in data entries come from each kind of source.

    Attributes:
        benchmarks: Entries measured by running the benchmark suite.
        spec_sheets: Entries taken from vendor documentation.
        external_analyses: Entries from third party measurement projects.
    """

    benchmarks: int
    spec_sheets: int
    external_analyses: int


def classified_source_keys() -> tuple[list[str], list[str], list[str]]:
    """Split the built-in data keys into (benchmarks, spec sheets, external analyses).

    Raises:
        ValueError: If a key matches none of the three, which means the dataset grew a kind of source
            this classification does not know about -- deliberately loud, since the alternative is a
            published count that quietly omits it.
    """
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


def source_counts() -> SourceCounts:
    """The three source-kind totals behind the shipped weights."""
    benchmarks, specs, third_party = classified_source_keys()
    return SourceCounts(
        benchmarks=len(benchmarks),
        spec_sheets=len(specs),
        external_analyses=len(third_party),
    )


# Named rather than derived. The keys do carry the project as a prefix, but turning
# `analysis_uops_info_zen3` into "uops.info" needs a hardcoded mapping either way -- one buried in
# parsing rather than written down -- and the set changes far too rarely to earn that.
THIRD_PARTY_PROJECTS = ["Agner Fog", "uops.info"]


def source_summary() -> str:
    """The dataset's composition, phrased once for every place that states it.

    Callers frame it -- the README as a bullet, the chart as a footnote -- but the counts, the
    wording and the named projects all come from here, so no two surfaces can end up describing the
    same dataset differently. The projects are named because the chart travels further than the
    README does: on the docs page and on PyPI it is the only place that says where the third-party
    figures came from.
    """
    counts = source_counts()
    return (
        f"{counts.benchmarks} benchmarks, {counts.spec_sheets} spec sheets, "
        f"{counts.external_analyses} third party measurements ({', '.join(THIRD_PARTY_PROJECTS)})"
    )
