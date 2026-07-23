import pytest

from counted_float._core.counting._builtin_data import BuiltInData, _flat_to_nested_dict, _load_json_files_as_dict
from counted_float._core.models import FlopsBenchmarkResults, FlopWeights


# =================================================================================================
#  Built-in benchmarks
# =================================================================================================
def test_builtin_data_benchmarks():
    # --- act ---------------------------------------------
    result = BuiltInData.benchmarks()

    # --- assert ------------------------------------------
    assert all(isinstance(v, FlopsBenchmarkResults) for v in result.values())
    assert len(result) == 21  # update as we add data


# =================================================================================================
#  FlopWeights
# =================================================================================================
@pytest.mark.parametrize("key_filter", [".", "benchmark", "specs", "analysis", "arm", "x86"])
def test_builtin_data_get_flop_weights(key_filter: str):
    # --- act ---------------------------------------------
    result = BuiltInData.get_flop_weights(key_filter=key_filter)

    # --- assert ------------------------------------------
    assert isinstance(result, FlopWeights)


def test_builtin_data_get_flop_weights_invalid_key():
    # --- arrange -----------------------------------------
    key_filter = "my_kitchen_sink"

    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="No built-in flop weights found"):
        BuiltInData.get_flop_weights(key_filter=key_filter)


@pytest.mark.parametrize(
    ("key_filter", "n_expected"),
    [
        (".", 49),
        ("benchmark", 21),
        ("analysis", 12),
        ("specs", 16),
        ("arm", 20),
        ("x86", 29),
    ],
)
def test_builtin_data_get_flop_weights_dict(key_filter: str, n_expected: int):
    # --- arrange -----------------------------------------
    full_dict = BuiltInData.get_flop_weights_dict()

    # --- act ---------------------------------------------
    results = BuiltInData.get_flop_weights_dict(key_filter=key_filter)

    # --- assert ------------------------------------------
    assert len(results) == n_expected
    assert all(key in full_dict for key in results)


# =================================================================================================
#  Visualization
# =================================================================================================
def test_built_in_data_show():
    # minimalistic test to at least check we don't raise exceptions
    BuiltInData.show()
    BuiltInData.show(key_filter="amd")


# =================================================================================================
#  Helpers
# =================================================================================================
def test_builtin_data_flat_to_nested_dict():
    # --- arrange -----------------------------------------
    flat_dict = {
        "a.b.c": 1,
        "a.b.d": 2,
        "a.e": 3,
        "f": 4,
    }
    expected_nested_dict = {
        "a": {
            "b": {
                "c": 1,
                "d": 2,
            },
            "e": 3,
        },
        "f": 4,
    }

    # --- act ---------------------------------------------
    nested_dict = _flat_to_nested_dict(flat_dict)

    # --- assert ------------------------------------------
    assert nested_dict == expected_nested_dict


class _FakeTraversable:
    """Stand-in for a zip/frozen-backed importlib.resources Traversable.

    Exposes only the guaranteed contract (name / is_dir / is_file / iterdir / read_text) and
    deliberately no `.stem`, so the loader is pinned to the pathlib-free Traversable surface.
    """

    def __init__(self, name, *, text=None, children=()):
        self.name = name
        self._text = text
        self._children = children

    def is_dir(self):
        return self._text is None

    def is_file(self):
        return self._text is not None

    def iterdir(self):
        return iter(self._children)

    def read_text(self, encoding="utf-8"):
        assert self._text is not None
        return self._text


def test_load_json_files_as_dict_uses_only_the_traversable_contract():
    # a resource backend without pathlib's `.stem` (zip / frozen installs) must still load
    # --- arrange -----------------------------------------
    root = _FakeTraversable(
        "sources",
        children=(
            _FakeTraversable("apple_m4_pro.json", text='{"cpu": "m4"}'),
            _FakeTraversable("notes.md", text="ignored"),
            _FakeTraversable("arm", children=(_FakeTraversable("graviton.json", text='{"cpu": "g"}'),)),
        ),
    )

    # --- act ---------------------------------------------
    result = _load_json_files_as_dict(root)

    # --- assert ------------------------------------------
    assert result == {"apple_m4_pro": '{"cpu": "m4"}', "arm.graviton": '{"cpu": "g"}'}
