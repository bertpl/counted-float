from __future__ import annotations

import math
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from ._base import MyBaseModel
from ._flop_type import FlopType
from ._flop_weights import FlopWeights


# =================================================================================================
#  Single-Instruction Latency
# =================================================================================================
class Latency(MyBaseModel):
    note: str = ""
    min_cycles: float | None = None
    max_cycles: float | None = None

    def geo_mean(self) -> float:
        """Calculate the geometric mean of min and max cycles."""
        if (self.min_cycles is None) or (self.max_cycles is None):
            return math.nan
        else:
            return math.sqrt(self.min_cycles * self.max_cycles)

    @model_validator(mode="before")
    @classmethod
    def check_min_max_cycles(cls, values):
        # Fill in missing values if just 1 of 2 is missing, assuming a 2x range
        if (values.get("min_cycles") is None) and (values.get("max_cycles") is not None):
            values["min_cycles"] = 0.5 * values["max_cycles"]
        elif (values.get("min_cycles") is not None) and (values.get("max_cycles") is None):
            values["max_cycles"] = 2.0 * values["min_cycles"]

        # Avoid 0 values.  (which in principle can happen in corner cases, but which confuses our analysis)
        if values.get("min_cycles") is not None:
            values["min_cycles"] = max(1.0, values["min_cycles"])
        if values.get("max_cycles") is not None:
            values["max_cycles"] = max(1.0, values["max_cycles"])

        # Return processed values
        return values


# =================================================================================================
#  InstructionLatencies - SSE2
# =================================================================================================
class InstructionLatencies_SSE2(MyBaseModel):
    # SEE: https://github.com/bertpl/counted-float/tree/develop/counted_float/data/fpu_data_sources.md

    # --- primary fields ----------------------------------
    architecture: Literal["sse2"] = "sse2"

    ANDPD: Latency | None = None  # abs(x)
    CVTSD2SI: Latency | None = None  # double -> int
    CVTSI2SD: Latency | None = None  # int -> double
    XORPD: Latency | None = None  # -x
    UCOMISD: Latency | None = None  # x < == > y, x < == > 0    NOTE: should be ranges of UCOMISD & COMISD merged
    MAXSD: Latency | None = None  # max(x,y)
    MINSD: Latency | None = None  # min(x,y)
    ADDSD: Latency | None = None  # x+y
    SUBSD: Latency | None = None  # x-y
    MULSD: Latency | None = None  # x*y
    DIVSD: Latency | None = None  # x/y
    SQRTSD: Latency | None = None  # sqrt(x)

    # --- helpers -----------------------------------------
    def flop_weights(self) -> FlopWeights:
        return FlopWeights.from_abs_flop_costs(
            {
                FlopType.ABS: _geo_mean_latency(self.ANDPD),
                FlopType.MINUS: _geo_mean_latency(self.XORPD),
                FlopType.EQUALS: _geo_mean_latency(self.UCOMISD),
                FlopType.GTE: _geo_mean_latency(self.UCOMISD),
                FlopType.LTE: _geo_mean_latency(self.UCOMISD),
                FlopType.CMP_ZERO: _geo_mean_latency(self.UCOMISD),
                FlopType.RND: _geo_mean_latency(self.CVTSD2SI),
                FlopType.ADD: _geo_mean_latency(self.ADDSD),
                FlopType.SUB: _geo_mean_latency(self.SUBSD),
                FlopType.MUL: _geo_mean_latency(self.MULSD),
                FlopType.DIV: _geo_mean_latency(self.DIVSD),
                FlopType.SQRT: _geo_mean_latency(self.SQRTSD),
            }
        )


# =================================================================================================
#  InstructionLatencies - ARM
# =================================================================================================
class InstructionLatencies_ARM(MyBaseModel):
    # SEE: https://github.com/bertpl/counted-float/tree/develop/counted_float/data/fpu_data_sources.md

    # --- primary fields ----------------------------------
    architecture: Literal["arm"] = "arm"

    FABS: Latency | None = None  # abs(x)
    FCVTZS: Latency | None = None  # double -> int
    SCVTF: Latency | None = None  # int -> double
    FNEG: Latency | None = None  # -x
    FCMP: Latency | None = None  # x < == > y, x < == > 0
    FMAX: Latency | None = None  # max(x,y)
    FMIN: Latency | None = None  # min(x,y)
    FADD: Latency | None = None  # x+y
    FSUB: Latency | None = None  # x-y
    FMUL: Latency | None = None  # x*y
    FDIV: Latency | None = None  # x/y
    FSQRT: Latency | None = None  # sqrt(x)

    # --- helpers -----------------------------------------
    def flop_weights(self) -> FlopWeights:
        return FlopWeights.from_abs_flop_costs(
            {
                FlopType.ABS: _geo_mean_latency(self.FABS),
                FlopType.MINUS: _geo_mean_latency(self.FNEG),
                FlopType.EQUALS: _geo_mean_latency(self.FCMP),
                FlopType.GTE: _geo_mean_latency(self.FCMP),
                FlopType.LTE: _geo_mean_latency(self.FCMP),
                FlopType.CMP_ZERO: _geo_mean_latency(self.FCMP),
                FlopType.RND: _geo_mean_latency(self.FCVTZS),
                FlopType.ADD: _geo_mean_latency(self.FADD),
                FlopType.SUB: _geo_mean_latency(self.FSUB),
                FlopType.MUL: _geo_mean_latency(self.FMUL),
                FlopType.DIV: _geo_mean_latency(self.FDIV),
                FlopType.SQRT: _geo_mean_latency(self.FSQRT),
            }
        )


# =================================================================================================
#  Union Class
# =================================================================================================
class InstructionLatencies(MyBaseModel):
    notes: list[str] | None = [""]
    latencies: Annotated[
        Union[
            InstructionLatencies_SSE2,
            InstructionLatencies_ARM,
        ],
        Field(discriminator="architecture"),
    ]

    def flop_weights(self) -> FlopWeights:
        return self.latencies.flop_weights()


# =================================================================================================
#  Misc helpers
# =================================================================================================
def _geo_mean_latency(lat: Latency | None) -> float:
    if isinstance(lat, Latency):
        return lat.geo_mean()
    else:
        return math.nan
