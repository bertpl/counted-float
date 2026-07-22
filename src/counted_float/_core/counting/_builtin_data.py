from __future__ import annotations

import json
import math
from functools import cache
from importlib.resources import files
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ValidationError
from rich.console import Console

from counted_float._core.models import (
    FlopsBenchmarkResults,
    FlopType,
    FlopWeights,
    InstructionLatencies,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from importlib.resources.abc import Traversable

PydanticModelT = TypeVar("PydanticModelT", bound=BaseModel)

DATA_PACKAGE = "counted_float.data"

# The source tree is crawled for every .json it contains, so it holds nothing but sources: derived
# artifacts live in sibling folders under the data package, out of the crawler's reach.
SOURCES_DIR = "sources"
PRECOMPUTED_DIR = "precomputed"
PRECOMPUTED_WEIGHTS_FILE = "consensus_flop_weights.json"


def _data_sources_root() -> Traversable:
    """Return the root of the built-in source data tree; source keys are relative to it."""
    return files(DATA_PACKAGE) / SOURCES_DIR


def _precomputed_weights_file() -> Traversable:
    """Return the shipped file holding aggregates already derived from the source tree."""
    return files(DATA_PACKAGE) / PRECOMPUTED_DIR / PRECOMPUTED_WEIGHTS_FILE


# =================================================================================================
#  Main accessor class
# =================================================================================================
class BuiltInData:
    """A class that provides access to built-in data for the counted_float package."""

    # -------------------------------------------------------------------------
    #  FlopWeights
    # -------------------------------------------------------------------------
    @classmethod
    def get_flop_weights(cls, key_filter: str = "") -> FlopWeights:
        """Return averaged FlopWeights over all FlopWeights from get_flop_weights_dict for the provided key_filter.

        Averaging happens one key-level at a time, which implicitly defines a recursive weighting scheme. At every level
        of aggregation, an attempt is made to impute missing data (if any) to avoid biasing the average towards entries
        with more complete data.

        The aggregation parses every source file, so results for the most-used key filters ship
        precomputed and are read from disk instead; any other filter is aggregated on the spot. The
        two paths agree by construction -- the shipped values are this method's own output, and a
        test re-derives them to keep it that way.
        """
        cached = _precomputed_flop_weights().get(key_filter)
        if cached is not None:
            return cached.model_copy(deep=True)  # callers may mutate what they get; the cache is shared
        return _aggregate_flop_weights_from_sources(key_filter)

    @classmethod
    def get_flop_weights_dict(cls, key_filter: str = "") -> dict[str, FlopWeights]:
        """Get the built-in flop weights data as a dict mapping key -> FlopWeights.

        Keys be .-separated values indicating the path + filename of the source data file, e.g.:
            'benchmarks.arm.apple_m4_pro'
            'specs.x86.intel_core_i9_13900k'
            ...

        :param key_filter: (str, default="") If non-empty, only include entries whose keys contain this substring.
        :return: A dictionary mapping benchmark names to their corresponding FlopsBenchmarkResults.
        """
        return {
            key: _construct_flop_weights_from_json_str(json_str)
            for key, json_str in _load_json_files_as_dict(_data_sources_root()).items()
            if key_filter in key
        }

    # -------------------------------------------------------------------------
    #  Benchmarks
    # -------------------------------------------------------------------------
    @classmethod
    def benchmarks(cls) -> dict[str, FlopsBenchmarkResults]:
        return {
            key: _deserialize_as_any_pydantic_class(json_str, [FlopsBenchmarkResults])
            for key, json_str in _load_json_files_as_dict(_data_sources_root()).items()
            if "benchmark" in key
        }

    # -------------------------------------------------------------------------
    #  Visualization
    # -------------------------------------------------------------------------
    @classmethod
    def show(cls, key_filter: str = "") -> None:
        """Show flow weights of all built-in data, optionally satisfying key_filter."""
        fw_nested_dict = _flat_to_nested_dict(cls.get_flop_weights_dict(key_filter))
        tree_view = FlopWeightsTreeView.from_nested_dict(name="ALL", nested_dict=fw_nested_dict)
        tree_view.show()


# =================================================================================================
#  Utilities
# =================================================================================================
def _aggregate_flop_weights_from_sources(key_filter: str = "") -> FlopWeights:
    """Aggregate the matching source files into one FlopWeights, bypassing the precomputed cache.

    This is the real computation BuiltInData.get_flop_weights() serves from cache where it can. The
    generator that writes that cache and the test that checks it both come through here, so neither
    can be fooled by a stale file.
    """
    flat_flop_weights_dict = BuiltInData.get_flop_weights_dict(key_filter)
    if len(flat_flop_weights_dict) == 0:
        raise ValueError(f"No built-in flop weights found for key_filter='{key_filter}'")
    return _compute_nested_average_flop_weights(_flat_to_nested_dict(flat_flop_weights_dict))


@cache
def _precomputed_flop_weights() -> dict[str, FlopWeights]:
    """Read the shipped aggregates: the key filter each was derived for -> its unrounded weights.

    Stored unrounded so one entry serves every rounding mode, which is applied on top by the caller.
    """
    raw: dict[str, dict[str, float | None]] = json.loads(
        _precomputed_weights_file().read_text(encoding="utf-8"),  # ty: ignore[unresolved-attribute] -- Path-like
    )
    # validate rather than construct: the stored form is JSON, with labels for keys and null for a
    # missing weight, which is exactly what the model's own validators already accept
    return {key_filter: FlopWeights.model_validate({"weights": weights}) for key_filter, weights in raw.items()}


def _compute_nested_average_flop_weights(nested_flop_weights_dict: dict[str, dict | FlopWeights]) -> FlopWeights:
    # make sure all values of the dict are FlopWeights instances
    for key, value in nested_flop_weights_dict.items():
        if isinstance(value, dict):
            nested_flop_weights_dict[key] = _compute_nested_average_flop_weights(value)

    # now we can average all FlopWeights instances
    # the loop above collapsed every dict value to FlopWeights; ty cannot track the mutation
    return FlopWeights.as_geo_mean(list(nested_flop_weights_dict.values()))  # ty: ignore[invalid-argument-type]


def _flat_to_nested_dict(flat_dict: dict) -> dict:
    """Convert a flat dict with .-separated keys to a nested dict.

    E.g. {'a.b.c': 1, 'a.b.d': 2, 'a.e': 3} -> {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}.
    """
    nested_dict = {}
    for flat_key, value in flat_dict.items():
        keys = flat_key.split(".")
        d = nested_dict
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
    return nested_dict


def _load_json_files_as_dict(resource_root: Traversable) -> dict[str, str]:
    """Read all .json files recursively from the given resource root and return a dict mapping key -> json_str.

    Keys are .-separated values indicating the path + filename of the source data file.

    Example keys: 'benchmarks.arm.apple_m4_pro'
                  'specs.x86.intel_core_i9_13900k'
    """
    # crawl entire folder structure
    result = {}
    for entry in resource_root.iterdir():
        if entry.is_dir():
            sub_dir_json_dict = _load_json_files_as_dict(entry)
            for key, value in sub_dir_json_dict.items():
                result[f"{entry.name}.{key}"] = value
        elif entry.is_file() and entry.name.endswith(".json"):
            result[entry.stem] = entry.read_text(encoding="utf-8")  # ty: ignore[unresolved-attribute] -- Path-like
    return result


def _construct_flop_weights_from_json_str(json_str: str) -> FlopWeights:
    """Construct a FlopWeights instance from a JSON string.

    The JSON string can represent either...
      - FlopsBenchmarkResults
      - InstructionLatencies_<x>
    :param json_str: (str) JSON string representing either of the aforementioned data structures.
    :return: FlopWeights instance extracted from the input data.
    """
    # try all supported classes, all of which have a .flop_weights property
    return _deserialize_as_any_pydantic_class(
        json_str,
        [
            FlopsBenchmarkResults,
            InstructionLatencies,
        ],
    ).flop_weights()


def _deserialize_as_any_pydantic_class(
    json_str: str,
    pydantic_classes: Sequence[type[PydanticModelT]],
) -> PydanticModelT:
    # try all supported classes
    for pydantic_cls in pydantic_classes:
        try:
            return pydantic_cls.model_validate_json(json_str)
        except ValidationError:
            continue

    # none of the supported classes worked
    raise ValueError("Input JSON string does not represent a known data structure.")


class FlopWeightsTreeView:
    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self, name: str, children: FlopWeights | list[FlopWeightsTreeView]) -> None:
        # --- init ----------------------------------------
        self.lst_indent: list[int] = []
        self.lst_is_leaf: list[bool] = []
        self.lst_tree_str: list[str] = []
        self.lst_flop_weights: list[FlopWeights] = []

        # --- populate ------------------------------------
        if isinstance(children, FlopWeights):
            # this is a LEAF
            self.lst_indent = [0]
            self.lst_is_leaf = [True]
            self.lst_tree_str = [name]
            self.lst_flop_weights = [children]
        else:
            # this is a BRANCH

            # 1] root node
            self.lst_indent = [0]
            self.lst_is_leaf = [False]
            self.lst_tree_str = [name]
            self.lst_flop_weights = [
                FlopWeights.as_geo_mean(
                    [
                        child.lst_flop_weights[0]  # = avg of each sub-branch
                        for child in children
                    ]
                )
            ]

            # 2] child nodes
            for i_child, child in enumerate(children):
                for i_line, (indent, is_leaf, tree_str, flop_weights) in enumerate(
                    zip(
                        child.lst_indent,
                        child.lst_is_leaf,
                        child.lst_tree_str,
                        child.lst_flop_weights,
                        strict=True,
                    )
                ):
                    self.lst_indent.append(1 + indent)
                    self.lst_is_leaf.append(is_leaf)
                    #
                    if i_child < len(children) - 1:
                        if i_line == 0:
                            self.lst_tree_str.append(f" \u251c\u2500{tree_str}")
                        else:
                            self.lst_tree_str.append(f" \u2502 {tree_str}")
                    else:
                        if i_line == 0:
                            self.lst_tree_str.append(f" \u2514\u2500{tree_str}")
                        else:
                            self.lst_tree_str.append(f"   {tree_str}")
                    self.lst_flop_weights.append(flop_weights)

    # -------------------------------------------------------------------------
    #  Visualization
    # -------------------------------------------------------------------------
    def show(self) -> None:
        # --- prep ----------------------------------------
        console = Console()
        console_width = console.width
        tree_width = 5 + max([len(line) for line in self.lst_tree_str])
        sorted_flop_types = self.lst_flop_weights[0].get_sorted_flop_types()
        # right-aligned cells carry their own inter-column gap in the padding, so a column must be
        # at least one character wider than its header not to glue onto its left neighbor
        col_widths = {flop_type: max(10, len(flop_type.name) + 1) for flop_type in sorted_flop_types}

        # greedy packing: a block takes columns while their cumulative width fits the console
        # (every block gets at least one column, so a too-narrow console still renders)
        flop_types_per_block: list[list[FlopType]] = []
        block_width = 0
        for flop_type in sorted_flop_types:
            if not flop_types_per_block or block_width + col_widths[flop_type] > console_width - tree_width:
                flop_types_per_block.append([])
                block_width = 0
            flop_types_per_block[-1].append(flop_type)
            block_width += col_widths[flop_type]

        # --- show data -----------------------------------
        for flop_types in flop_types_per_block:
            # --- legend ---
            legend = " " * tree_width
            for flop_type in flop_types:
                legend += flop_type.name.rjust(col_widths[flop_type])
            console.print(legend, style="bold")

            # --- actual tree view ---
            for indent, is_leaf, tree_str, flop_weights in zip(
                self.lst_indent,
                self.lst_is_leaf,
                self.lst_tree_str,
                self.lst_flop_weights,
                strict=True,
            ):
                line = tree_str.ljust(tree_width)
                for flop_type in flop_types:
                    w = flop_weights.weights[flop_type]
                    if math.isnan(w):
                        line += "/ ".rjust(col_widths[flop_type])
                    elif isinstance(w, int):
                        line += str(w).rjust(col_widths[flop_type])
                    else:
                        line += f"{w:.2f}".rjust(col_widths[flop_type])

                if is_leaf:
                    # no special styling
                    console.print(line, highlight=False)
                else:
                    # highlight as bold and with a colored background.  The two bright bars pin a
                    # dark gray foreground instead of leaving it to the terminal default, which on
                    # dark themes is a light gray they leave barely legible (on the green one it
                    # all but disappears).  The darker bars keep the default, which reads fine on
                    # them either way.
                    style_tag = [
                        "[bold on #888888]",  # indent 0
                        "[bold on #7777dd]",  # indent 1
                        "[bold #333333 on #77dd77]",  # indent 2
                        "[bold #333333 on #ee7777]",  # indent 3
                        "[bold italic]",  # indent 4+
                    ][min(indent, 4)]
                    line = line[: 3 * indent] + style_tag + line[3 * indent :] + "[/]"
                    console.print(line, highlight=False)

            print()

    # -------------------------------------------------------------------------
    #  Factory methods
    # -------------------------------------------------------------------------
    @classmethod
    def from_nested_dict(cls, name: str, nested_dict: dict[str, dict | FlopWeights]) -> FlopWeightsTreeView:
        members = []
        for key in sorted(nested_dict.keys()):
            value = nested_dict[key]
            if isinstance(value, FlopWeights):
                members.append(FlopWeightsTreeView(name=key, children=value))
            else:
                members.append(FlopWeightsTreeView.from_nested_dict(name=key, nested_dict=value))

        return FlopWeightsTreeView(name=name, children=members)
