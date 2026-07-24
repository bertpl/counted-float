from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ValidationError

from counted_float._core.models import (
    FlopsBenchmarkResults,
    FlopWeights,
    InstructionLatencies,
)

from ._flop_weights_tree_view import FlopWeightsTreeView

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


# a source tree is str-keyed all the way down: each level maps a name to either a deeper level or a
# leaf FlopWeights. Recursive so the isinstance-driven descent below type-checks against itself.
NestedFlopWeights = dict[str, "NestedFlopWeights | FlopWeights"]


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


def _compute_nested_average_flop_weights(nested_flop_weights_dict: NestedFlopWeights) -> FlopWeights:
    # make sure all values of the dict are FlopWeights instances
    for key, value in nested_flop_weights_dict.items():
        if isinstance(value, dict):
            nested_flop_weights_dict[key] = _compute_nested_average_flop_weights(value)

    # now we can average all FlopWeights instances
    # the loop above collapsed every dict value to FlopWeights; ty cannot track the mutation
    return FlopWeights.as_geo_mean(list(nested_flop_weights_dict.values()))  # ty: ignore[invalid-argument-type]


def _flat_to_nested_dict(flat_dict: dict[str, FlopWeights]) -> NestedFlopWeights:
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
            result[entry.name.removesuffix(".json")] = entry.read_text(encoding="utf-8")
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
