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
#  Cross-architecture flop-type coverage
# =================================================================================================
def test_sse2_and_arm_model_the_same_set_of_flop_types():
    """Ensure InstructionLatencies_SSE2 and InstructionLatencies_ARM model the same flop types.

    Each class maps flop types onto its own architecture's instruction fields, and the two maps are
    independent literals that nothing compares. A flop type added to one and not the other leaves
    the architectures covering different operations, with the all-architecture consensus then
    aggregated over inputs that do not span the same ground.

    Giving every instruction a distinct latency checks the mapping rather than only its key set: two
    flop types wired to one instruction, or a swapped pair, show up as a wrong weight here.
    """

    # --- arrange -----------------------------------------
    # distinct cycles per field, so each flop type's weight identifies the instruction behind it.
    # Only the mapped types get a value: `weights` spans every FlopType, with NaN meaning "this
    # architecture says nothing about it", so comparing raw key sets would compare nothing.
    def _weights_by_flop_type(model_cls) -> dict:
        fields = [name for name in model_cls.model_fields if name != "architecture"]
        model = model_cls(
            **{name: Latency(min_cycles=float(i), max_cycles=float(i)) for i, name in enumerate(fields, start=1)}
        )
        return {flop_type: w for flop_type, w in model.flop_weights().weights.items() if not math.isnan(w)}

    # --- act ---------------------------------------------
    sse2 = _weights_by_flop_type(InstructionLatencies_SSE2)
    arm = _weights_by_flop_type(InstructionLatencies_ARM)

    # --- assert ------------------------------------------
    assert set(sse2) == set(arm), (
        f"only in sse2: {sorted(t.name for t in set(sse2) - set(arm))}; "
        f"only in arm: {sorted(t.name for t in set(arm) - set(sse2))}"
    )
    assert sse2, "neither architecture modelled anything -- this test would pass over nothing"
    # a distinct instruction per flop type must stay distinct through the mapping
    assert len(set(sse2.values())) == len(sse2), f"two flop types share an instruction in sse2: {sse2}"
    assert len(set(arm.values())) == len(arm), f"two flop types share an instruction in arm: {arm}"
