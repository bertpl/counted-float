"""The shipped data files must key FlopType dicts on stable names.

These guard the label->name key migration: every serialized FlopType-keyed dict in the source tree
and the precomputed aggregate keys on the stable member name, and all of them parse -- the reader
accepts nothing else (legacy label keys raise; pre-2.0.0 files must be regenerated).
"""

import json

from counted_float._core.counting.builtin_data.dataset import (
    _data_sources_root,
    _load_json_files_as_dict,
    _precomputed_weights_file,
)
from counted_float._core.models import FlopsBenchmarkResults, FlopType

_CANONICAL_NAMES = {ft.name for ft in FlopType}


def _shipped_flop_type_keyed_dicts() -> list[tuple[str, dict]]:
    """Return (source_key, flop-type-keyed dict) for every such dict in the shipped data tree."""
    found: list[tuple[str, dict]] = []
    for key, json_str in _load_json_files_as_dict(_data_sources_root()).items():
        data = json.loads(json_str)
        if "estimated_flop_latencies" in data:  # benchmark files; specs key on mnemonics instead
            found.append((key, data["estimated_flop_latencies"]))
    precomputed = json.loads(_precomputed_weights_file().read_text(encoding="utf-8"))
    found.extend((f"precomputed[{filt!r}]", weights) for filt, weights in precomputed.items())
    return found


def test_shipped_data_files_key_on_stable_names() -> None:
    # --- act / assert ------------------------------------
    for source_key, flop_dict in _shipped_flop_type_keyed_dicts():
        unexpected = set(flop_dict) - _CANONICAL_NAMES
        assert not unexpected, f"{source_key}: non-name keys {sorted(unexpected)} (migrate to stable names)"


def test_every_builtin_benchmark_result_still_parses() -> None:
    """Sanity: the migrated benchmark files load as FlopsBenchmarkResults with name-keyed latencies."""
    # --- arrange -----------------------------------------
    from counted_float._core.counting import BuiltInData

    # --- act / assert ------------------------------------
    results = BuiltInData.benchmarks()
    assert results, "expected shipped benchmark results"
    for key, result in results.items():
        assert isinstance(result, FlopsBenchmarkResults)
        assert set(result.estimated_flop_latencies) <= set(FlopType), key
