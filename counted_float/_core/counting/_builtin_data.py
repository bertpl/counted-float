from __future__ import annotations

import math
from importlib.resources import files

from pydantic import BaseModel, ValidationError
from rich.console import Console

from counted_float._core.models import (
    FlopsBenchmarkResults,
    FlopWeights,
    InstructionLatencies,
)

DATA_PACKAGE = "counted_float.data"


# =================================================================================================
#  Main accessor class
# =================================================================================================
class BuiltInData:
    """
    A class that provides access to built-in data for the counted_float package.
    """

    # -------------------------------------------------------------------------
    #  FlopWeights
    # -------------------------------------------------------------------------
    @classmethod
    def get_flop_weights(cls, key_filter: str = "") -> FlopWeights:
        """
        Return averaged FlopWeights over all FlopWeights found using get_flop_weights_dict for the provided key_filter.

        Averaging happens one key-level at a time, which implicitly defines a recursive weighting scheme. At every level
        of aggregation, an attempt is made to impute missing data (if any) to avoid biasing the average towards entries
        with more complete data.
        """
        flat_flop_weights_dict = cls.get_flop_weights_dict(key_filter)
        if len(flat_flop_weights_dict) == 0:
            raise ValueError(f"No built-in flop weights found for key_filter='{key_filter}'")
        else:
            nested_flop_weights_dict = _flat_to_nested_dict(flat_flop_weights_dict)
            return _computed_nested_average_flop_weights(nested_flop_weights_dict)

    @classmethod
    def get_flop_weights_dict(cls, key_filter: str = "") -> dict[str, FlopWeights]:
        """
        Get the built-in flop weights data as a dict mapping key -> FlopWeights.

        Keys be .-separated values indicating the path + filename of the source data file, e.g.:
            'benchmarks.arm.apple_m4_pro'
            'specs.x86.intel_core_i9_13900k'
            ...

        :param key_filter: (str, default="") If non-empty, only include entries whose keys contain this substring.
        :return: A dictionary mapping benchmark names to their corresponding FlopsBenchmarkResults.
        """
        return {
            key: _construct_flop_weights_from_json_str(json_str)
            for key, json_str in _load_json_files_as_dict(files(DATA_PACKAGE)).items()
            if key_filter in key
        }

    # -------------------------------------------------------------------------
    #  Benchmarks
    # -------------------------------------------------------------------------
    @classmethod
    def benchmarks(cls) -> dict[str, FlopsBenchmarkResults]:
        return {
            key: _deserialize_as_any_pydantic_class(json_str, [FlopsBenchmarkResults])
            for key, json_str in _load_json_files_as_dict(files(f"{DATA_PACKAGE}")).items()
            if "benchmark" in key
        }

    # -------------------------------------------------------------------------
    #  Visualization
    # -------------------------------------------------------------------------
    @classmethod
    def show(cls, key_filter: str = ""):
        """Show flow weights of all built-in data, optionally satisfying key_filter."""
        fw_nested_dict = _flat_to_nested_dict(cls.get_flop_weights_dict(key_filter))
        tree_view = FlopWeightsTreeView.from_nested_dict(name="ALL", nested_dict=fw_nested_dict)
        tree_view.show()


# =================================================================================================
#  Utilities
# =================================================================================================
def _computed_nested_average_flop_weights(nested_flop_weights_dict: dict[str, dict | FlopWeights]) -> FlopWeights:
    # make sure all values of the dict are FlopWeights instances
    for key, value in nested_flop_weights_dict.items():
        if isinstance(value, dict):
            nested_flop_weights_dict[key] = _computed_nested_average_flop_weights(value)

    # now we can average all FlopWeights instances
    return FlopWeights.as_geo_mean(list(nested_flop_weights_dict.values()))


def _flat_to_nested_dict(flat_dict: dict) -> dict:
    """
    Convert a flat dict with .-separated keys to a nested dict.
    E.g. {'a.b.c': 1, 'a.b.d': 2, 'a.e': 3} -> {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}
    """
    nested_dict = {}
    for flat_key, value in flat_dict.items():
        keys = flat_key.split(".")
        d = nested_dict
        for key in keys[:-1]:
            d = d.setdefault(key, dict())
        d[keys[-1]] = value
    return nested_dict


def _load_json_files_as_dict(resource_root) -> dict[str, str]:
    """
    Read all .json files recursively from the given resource root (or the default one) and return
    a dict mapping key -> json_str, where keys are .-separated values indicating the path
        + filename of the source data file.

    Example keys: 'benchmarks.arm.apple_m4_pro'
                  'specs.x86.intel_core_i9_13900k'
    """

    # allow both plain & recursive calls
    # if resource_root is None:
    #     resource_root = files("counted_float._core.data")

    # crawl entire folder structure
    result = {}
    for entry in resource_root.iterdir():
        if entry.is_dir():
            sub_dir_json_dict = _load_json_files_as_dict(entry)
            for key, value in sub_dir_json_dict.items():
                result[f"{entry.name}.{key}"] = value
        elif entry.is_file() and entry.name.endswith(".json"):
            result[entry.stem] = entry.read_text(encoding="utf-8")
    return result


def _construct_flop_weights_from_json_str(json_str: str) -> FlopWeights:
    """
    Construct a FlopWeights instance from a JSON string, where the JSON string can represent either...
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


def _deserialize_as_any_pydantic_class(json_str: str, pydantic_classes: list[type[BaseModel]]):
    # try all supported classes
    for pydantic_cls in pydantic_classes:
        try:
            obj = pydantic_cls.model_validate_json(json_str)
            return obj
        except ValidationError:
            continue

    # none of the supported classes worked
    raise ValueError("Input JSON string does not represent a known data structure.")


class FlopWeightsTreeView:
    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self, name: str, children: FlopWeights | list[FlopWeightsTreeView]):
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
    def show(self):
        # --- prep ----------------------------------------
        console = Console()
        console_width = console.width
        tree_width = 5 + max([len(line) for line in self.lst_tree_str])
        col_width = 10
        sorted_flop_types = self.lst_flop_weights[0].get_sorted_flop_types()
        max_indent = max(self.lst_indent)

        n_cols_per_block = max(1, int((console_width - tree_width) / col_width))
        flop_types_per_block = [
            sorted_flop_types[i_start : i_start + n_cols_per_block]
            for i_start in range(0, len(sorted_flop_types), n_cols_per_block)
        ]

        # --- show data -----------------------------------
        for flop_types in flop_types_per_block:
            # --- legend ---
            legend = " " * tree_width
            for flop_type in flop_types:
                legend += flop_type.name.rjust(col_width)
            console.print(legend, style="bold")

            # --- actual tree view ---
            for indent, is_leaf, tree_str, flop_weights in zip(
                self.lst_indent,
                self.lst_is_leaf,
                self.lst_tree_str,
                self.lst_flop_weights,
            ):
                line = tree_str.ljust(tree_width)
                for flop_type in flop_types:
                    w = flop_weights.weights[flop_type]
                    if math.isnan(w):
                        line += "/ ".rjust(col_width)
                    elif isinstance(w, int):
                        line += str(w).rjust(col_width)
                    else:
                        line += f"{w:.2f}".rjust(col_width)

                if is_leaf:
                    # no special styling
                    console.print(line, highlight=False)
                else:
                    # highlight as bold and with a colored background
                    style_tag = [
                        "[bold on #888888]",  # indent 0
                        "[bold on #7777dd]",  # indent 1
                        "[bold on #77dd77]",  # indent 2
                        "[bold on #ee7777]",  # indent 3
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
