from __future__ import annotations

import math
from typing import Iterable

from pydantic import field_serializer, field_validator

from ._base import MyBaseModel
from ._flop_type import FlopType


class FlopWeights(MyBaseModel):
    weights: dict[FlopType, float | int]

    # -------------------------------------------------------------------------
    #  Helpers
    # -------------------------------------------------------------------------
    def round(self) -> FlopWeights:
        """Round all weights to the nearest integer, with minimum of 1."""
        return FlopWeights(
            weights={k: max(1, round(v)) for k, v in self.weights.items()},
        )

    # -------------------------------------------------------------------------
    #  Validation
    # -------------------------------------------------------------------------
    @field_validator("weights")
    @classmethod
    def check_all_flop_types_present(cls, v: dict[FlopType, float | int]) -> dict[FlopType, float | int]:
        # make sure all FlopType enum members are present
        missing = [member for member in FlopType if member not in v]
        if missing:
            raise ValueError(f"Missing weights for flop types: {missing}")
        return v

    @field_serializer("weights")
    def serialize_weights(self, weights: dict[FlopType, float | int]) -> dict[str, float | int]:
        # make sure we serialize using the enum values as keys
        return {k.value: v for k, v in weights.items()}

    # -------------------------------------------------------------------------
    #  Factory methods
    # -------------------------------------------------------------------------
    @classmethod
    def as_geo_mean(cls, all_flop_weights: Iterable[FlopWeights]) -> FlopWeights:
        """Computes geo-mean of a collection of FlopWeights instances."""
        all_flop_weights = list(all_flop_weights)
        return FlopWeights(
            weights={
                flop_type: pow(
                    math.prod(fw.weights[flop_type] for fw in all_flop_weights),
                    1 / len(all_flop_weights),
                )  # take geometric mean of all weights for this flop_type
                for flop_type in FlopType
            }
        )

    @classmethod
    def from_abs_flop_costs(cls, flop_costs: dict[FlopType, float]) -> FlopWeights:
        """
        Computes FlopWeights based on absolute costs (in clock cycles, nanoseconds, ...) of each flop type.
        As a reference duration, we take the geometric mean of the costs for EQUALS, ADD, SUB, and MUL operations.
        """

        # step 1) compute reference duration
        ref_cost = (
            flop_costs[FlopType.EQUALS] * flop_costs[FlopType.ADD] * flop_costs[FlopType.SUB] * flop_costs[FlopType.MUL]
        ) ** (1 / 4)

        # step 2) normalize and construct FlopWeights object
        return FlopWeights(
            weights={flop_type: flop_cost / ref_cost for flop_type, flop_cost in flop_costs.items()},
        )
