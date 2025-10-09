import math

import pytest

from counted_float._core.models._instruction_latencies import (
    InstructionLatencies,
    InstructionLatencies_ARM,
    InstructionLatencies_SSE2,
    Latency,
)


# =================================================================================================
#  Latency
# =================================================================================================
@pytest.mark.parametrize(
    "min_cycles, max_cycles, expected_consensus",
    [
        (1.0, 4.0, 4.0),
        (0.0, 3.0, 3.0),
        (0.0, 0.0, 1.0),
        (None, 2.0, 2.0),
        (1.0, None, 1.0),
        (None, 0.0, 1.0),
        (0.0, None, 1.0),
        (None, None, math.nan),
    ],
)
def test_latency_geomean(min_cycles: float | None, max_cycles: float | None, expected_consensus: float):
    # --- arrange -----------------------------------------
    latency = Latency(min_cycles=min_cycles, max_cycles=max_cycles)

    # --- act ---------------------------------------------
    geo_mean = latency.consensus()

    # --- assert ------------------------------------------
    if math.isnan(expected_consensus):
        assert math.isnan(geo_mean)
    else:
        assert geo_mean == expected_consensus


# =================================================================================================
#  InstructionLatencies
# =================================================================================================
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
