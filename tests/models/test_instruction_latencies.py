import pytest

from counted_float._core.models._instruction_latencies import (
    InstructionLatencies,
    InstructionLatencies_ARM,
    InstructionLatencies_SSE2,
)


@pytest.mark.parametrize(
    "pydantic_cls",
    [
        InstructionLatencies_ARM,
        InstructionLatencies_SSE2,
    ],
)
def test_instruction_latencies_deserialization(pydantic_cls):
    # --- arrange -----------------------------------------
    obj = InstructionLatencies(latencies=pydantic_cls())
    obj_dict = obj.model_dump()

    # --- act ---------------------------------------------
    deser_obj = InstructionLatencies.model_validate(obj_dict)

    # --- assert ------------------------------------------
    assert isinstance(deser_obj.latencies, pydantic_cls)
