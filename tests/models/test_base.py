from pydantic import field_serializer

from counted_float._core.models._base import JsonReprModel


class _Sample(JsonReprModel):
    a: int
    b: str


class _DisplayAware(JsonReprModel):
    v: int

    @field_serializer("v")
    def _serialize_v(self, v, info):
        # renders differently under the {"display": True} context that JsonReprModel.__str__/show pass
        return "shown" if (info.context or {}).get("display") else "stored"


def test_str_renders_indented_json():
    # --- act ---------------------------------------------
    result = str(_Sample(a=1, b="hello"))

    # --- assert ------------------------------------------
    assert result == '{\n    "a": 1,\n    "b": "hello"\n}'


def test_repr_matches_str():
    # --- arrange -----------------------------------------
    model = _Sample(a=1, b="hello")

    # --- act & assert ------------------------------------
    assert repr(model) == str(model)


def test_show_prints_the_str_rendering(capsys):
    # --- act ---------------------------------------------
    _Sample(a=1, b="hello").show()

    # --- assert ------------------------------------------
    assert capsys.readouterr().out == '{\n    "a": 1,\n    "b": "hello"\n}\n'


def test_str_passes_the_display_context():
    # --- act & assert ------------------------------------
    assert '"v": "shown"' in str(_DisplayAware(v=1))


def test_show_passes_the_display_context(capsys):
    # --- act ---------------------------------------------
    _DisplayAware(v=1).show()

    # --- assert ------------------------------------------
    assert '"v": "shown"' in capsys.readouterr().out
