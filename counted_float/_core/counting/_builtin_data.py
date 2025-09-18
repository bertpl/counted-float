from importlib.resources import files

from pydantic import ValidationError

from counted_float._core.counting.models import FlopsBenchmarkResults, FlopWeights, InstructionLatencies


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
            for key, json_str in _load_json_files_as_dict(files("counted_float._core.data")).items()
            if key_filter in key
        }

    # -------------------------------------------------------------------------
    #  Benchmarks
    # -------------------------------------------------------------------------
    @classmethod
    def benchmarks(cls) -> dict[str, FlopsBenchmarkResults]:
        return {
            key: FlopsBenchmarkResults.model_validate_json(json_str)
            for key, json_str in _load_json_files_as_dict(files("counted_float._core.data.benchmarks")).items()
        }

    # -------------------------------------------------------------------------
    #  Specs
    # -------------------------------------------------------------------------
    @classmethod
    def specs(cls) -> dict[str, InstructionLatencies]:
        return {
            key: InstructionLatencies.model_validate_json(json_str)
            for key, json_str in _load_json_files_as_dict(files("counted_float._core.data.specs")).items()
        }


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
      - InstructionLatencies
    :param json_str: (str) JSON string representing either of the aforementioned data structures.
    :return: FlopWeights instance extracted from the input data.
    """

    # try all supported classes, all of which have a .flop_weights property
    for pydantic_cls in [FlopsBenchmarkResults, InstructionLatencies]:
        try:
            obj = pydantic_cls.model_validate_json(json_str)
            return obj.flop_weights
        except ValidationError:
            continue

    # none of the supported classes worked
    raise ValueError("Input JSON string does not represent a known data structure.")
