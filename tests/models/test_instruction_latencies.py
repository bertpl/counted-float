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
    ("min_cycles", "max_cycles", "expected_consensus"),
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


def test_latency_consensus_is_the_larger_of_min_and_max_cycles():
    # consensus takes max(min, max) -- even when min exceeds max, so a mutant that drops min_cycles
    # (returning only the max) is caught
    # --- act & assert ------------------------------------
    assert Latency(min_cycles=5.0, max_cycles=3.0).consensus() == 5.0
    assert Latency(min_cycles=2.0, max_cycles=8.0).consensus() == 8.0


# =================================================================================================
#  The two architectures must price the same set of flop types
# =================================================================================================
def test_both_architectures_price_the_same_flop_types():
    """Neither architecture may price an operation the other does not.

    Each class maps flop types onto its own architecture's instruction fields, and the two maps are
    independent literals -- nothing compares them. Add a flop type to one and forget the other and
    no existing test fails: the two simply cover different operations, and the all-architecture
    consensus is then aggregated from inputs that do not span the same ground.

    No mutant corresponds to this. The defect it guards is a missing entry rather than a wrong
    expression, so mutation testing cannot reach it and a test is the only thing that can.
    """

    # --- arrange -----------------------------------------
    # every instruction field given the same finite latency: the weights are irrelevant here, only
    # which flop types come out, and a default-constructed model has no finite ADD to normalize by
    def _filled(model_cls):
        fields = {
            name: Latency(min_cycles=1.0, max_cycles=1.0) for name in model_cls.model_fields if name != "architecture"
        }
        return model_cls(**fields)

    # --- act ---------------------------------------------
    sse2_types = set(_filled(InstructionLatencies_SSE2).flop_weights().weights)
    arm_types = set(_filled(InstructionLatencies_ARM).flop_weights().weights)

    # --- assert ------------------------------------------
    assert sse2_types == arm_types, (
        f"only in sse2: {sorted(t.name for t in sse2_types - arm_types)}; "
        f"only in arm: {sorted(t.name for t in arm_types - sse2_types)}"
    )
    assert sse2_types, "both maps are empty -- this test would pass over nothing"
