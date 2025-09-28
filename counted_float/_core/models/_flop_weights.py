from __future__ import annotations

import math
from typing import Iterable

import numpy as np
from pydantic import field_serializer, field_validator

from counted_float._core.utils import geo_mean, impute_missing_data

from ._base import MyBaseModel
from ._flop_type import FlopType


class FlopWeights(MyBaseModel):
    weights: dict[FlopType, float | int]  # note: math.nan will indicate "unknown" weights  (e.g. missing FPU specs)

    # -------------------------------------------------------------------------
    #  Helpers
    # -------------------------------------------------------------------------
    def round(self) -> FlopWeights:
        """Round all weights to the nearest integer, with minimum of 1."""
        return FlopWeights(
            weights={k: math.nan if math.isnan(v) else max(1, round(v)) for k, v in self.weights.items()},
        )

    def has_missing_data(self) -> bool:
        """Check if any flop type has missing data (i.e. weight is NaN)."""
        return any(math.isnan(v) for v in self.weights.values())

    def get_sorted_flop_types(self) -> list[FlopType]:
        """Return flop types sorted in ascending order of corresponding weights."""
        sorted_flop_weights_and_types = sorted(zip(self.weights.values(), self.weights.keys()))
        return [flop_type for _, flop_type in sorted_flop_weights_and_types]

    # -------------------------------------------------------------------------
    #  Validation
    # -------------------------------------------------------------------------
    @field_validator("weights")
    @classmethod
    def ensure_all_flop_types_present(cls, v: dict[FlopType, float | int]) -> dict[FlopType, float | int]:
        # make sure all FlopType enum members are present
        for flop_type in FlopType:
            if flop_type not in v:
                v[flop_type] = math.nan
        return v

    @field_serializer("weights")
    def serialize_weights(self, weights: dict[FlopType, float | int]) -> dict[str, float | int]:
        # make sure we serialize using the enum values as keys
        return {k.value: v for k, v in weights.items()}

    # -------------------------------------------------------------------------
    #  Custom visualization
    # -------------------------------------------------------------------------
    def show(self):
        print("{")
        for k, v in self.weights.items():
            if isinstance(v, float):
                print(f"    {k.long_name()}".ljust(40) + f": {v:9.5f}")
            else:
                print(f"    {k.long_name()}".ljust(40) + f": {v:>4}")
        print("}")

    # -------------------------------------------------------------------------
    #  Factory methods
    # -------------------------------------------------------------------------
    @classmethod
    def as_geo_mean(cls, all_flop_weights: Iterable[FlopWeights], fill_missing_data: bool = True) -> FlopWeights:
        """Computes geo-mean of a collection of FlopWeights instances."""

        # --- prep ----------------------------------------
        all_flop_weights = list(all_flop_weights)

        # put in numpy array for easier processing
        w = np.zeros(shape=(len(FlopType), len(all_flop_weights)), dtype=float)
        for i_row, flop_type in enumerate(FlopType):
            for i_col, fw in enumerate(all_flop_weights):
                w[i_row, i_col] = fw.weights[flop_type]

        # --- fill missing data ---------------------------
        if (
            fill_missing_data
            and (len(all_flop_weights) > 1)
            and any([fw.has_missing_data() for fw in all_flop_weights])
        ):
            w = impute_missing_data(w)

        # --- compute geo_mean ----------------------------
        return FlopWeights(
            weights={
                flop_type: geo_mean(
                    [float(w_i) for w_i in w[i, :]]
                )  # take geo_mean of row (will return nan if any value is nan)
                for i, flop_type in enumerate(FlopType)
            }
        )

    @classmethod
    def from_abs_flop_costs(cls, flop_costs: dict[FlopType, float]) -> FlopWeights:
        """
        Computes FlopWeights based on absolute costs (in clock cycles, nanoseconds, ...) of each flop type.
        As a reference duration, we take the geometric mean of the costs for EQUALS, ADD, SUB, and MUL operations.
        """

        # step 1) compute reference duration based on 1 simple flop type (SUB, MUL and a few others are usually very close)
        ref_cost = flop_costs[FlopType.ADD]

        # step 2) normalize and construct FlopWeights object
        return FlopWeights(
            weights={flop_type: flop_cost / ref_cost for flop_type, flop_cost in flop_costs.items()},
        )
