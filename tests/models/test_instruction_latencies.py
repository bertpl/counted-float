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
    "min_cycles, max_cycles, expected_min_cycles, expected_max_cycles",
    [
        (1.0, 1.0, 1.0, 1.0),
        (1.0, 2.0, 1.0, 2.0),
        (1.0, 10.0, 1.0, 10.0),
        (None, 10.0, 5.0, 10.0),
        (1.0, None, 1.0, 2.0),
        (None, None, None, None),
        (0.0, 1.0, 1.0, 1.0),
        (0.0, 0.0, 1.0, 1.0),
    ],
    ids=[
        "normal_1",
        "normal_2",
        "normal_3",
        "min_cycles_missing",
        "max_cycles_missing",
        "both_missing",
        "min_cycles_0",
        "both_0",
    ],
)
def test_latency_missing_values(
    min_cycles: float | None,
    max_cycles: float | None,
    expected_min_cycles: float | None,
    expected_max_cycles: float | None,
):
    # --- act ---------------------------------------------
    latency = Latency(min_cycles=min_cycles, max_cycles=max_cycles)

    # --- assert ------------------------------------------
    assert latency.min_cycles == expected_min_cycles
    assert latency.max_cycles == expected_max_cycles


@pytest.mark.parametrize(
    "min_cycles, max_cycles, expected_geo_mean",
    [
        (1.0, 4.0, 2.0),
        (None, None, math.nan),
    ],
)
def test_latency_geomean(min_cycles: float | None, max_cycles: float | None, expected_geo_mean: float):
    # --- arrange -----------------------------------------
    latency = Latency(min_cycles=min_cycles, max_cycles=max_cycles)

    # --- act ---------------------------------------------
    geo_mean = latency.geo_mean()

    # --- assert ------------------------------------------
    if math.isnan(expected_geo_mean):
        assert math.isnan(geo_mean)
    else:
        assert geo_mean == expected_geo_mean


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
