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
        # Fill in missing values if just 1 of 2 is missing
        #   (assuming min=max; which is making the least assumptions, as this is the case in most instructions)
        if (values.get("min_cycles") is None) and (values.get("max_cycles") is not None):
            values["min_cycles"] = values["max_cycles"]
        elif (values.get("min_cycles") is not None) and (values.get("max_cycles") is None):
            values["max_cycles"] = values["min_cycles"]

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

    ANDPD: Latency = Latency()  # abs(x)
    CVTSD2SI: Latency = Latency()  # double -> int
    CVTSI2SD: Latency = Latency()  # int -> double
    XORPD: Latency = Latency()  # -x
    UCOMISD: Latency = Latency()  # x < == > y, x < == > 0    NOTE: should be ranges of UCOMISD & COMISD merged
    MAXSD: Latency = Latency()  # max(x,y)
    MINSD: Latency = Latency()  # min(x,y)
    ADDSD: Latency = Latency()  # x+y
    SUBSD: Latency = Latency()  # x-y
    MULSD: Latency = Latency()  # x*y
    DIVSD: Latency = Latency()  # x/y
    SQRTSD: Latency = Latency()  # sqrt(x)

    # --- helpers -----------------------------------------
    def flop_weights(self) -> FlopWeights:
        return FlopWeights.from_abs_flop_costs(
            {
                FlopType.ABS: self.ANDPD.geo_mean(),
                FlopType.MINUS: self.XORPD.geo_mean(),
                FlopType.EQUALS: self.UCOMISD.geo_mean(),
                FlopType.GTE: self.UCOMISD.geo_mean(),
                FlopType.LTE: self.UCOMISD.geo_mean(),
                FlopType.CMP_ZERO: self.UCOMISD.geo_mean(),
                FlopType.RND: self.CVTSD2SI.geo_mean(),
                FlopType.ADD: self.ADDSD.geo_mean(),
                FlopType.SUB: self.SUBSD.geo_mean(),
                FlopType.MUL: self.MULSD.geo_mean(),
                FlopType.DIV: self.DIVSD.geo_mean(),
                FlopType.SQRT: self.SQRTSD.geo_mean(),
            }
        )


# =================================================================================================
#  InstructionLatencies - ARM
# =================================================================================================
class InstructionLatencies_ARM(MyBaseModel):
    # SEE: https://github.com/bertpl/counted-float/tree/develop/counted_float/data/fpu_data_sources.md

    # --- primary fields ----------------------------------
    architecture: Literal["arm"] = "arm"

    FABS: Latency = Latency()  # abs(x)
    FCVTZS: Latency = Latency()  # double -> int
    SCVTF: Latency = Latency()  # int -> double
    FNEG: Latency = Latency()  # -x
    FCMP: Latency = Latency()  # x < == > y, x < == > 0
    FMAX: Latency = Latency()  # max(x,y)
    FMIN: Latency = Latency()  # min(x,y)
    FADD: Latency = Latency()  # x+y
    FSUB: Latency = Latency()  # x-y
    FMUL: Latency = Latency()  # x*y
    FDIV: Latency = Latency()  # x/y
    FSQRT: Latency = Latency()  # sqrt(x)

    # --- helpers -----------------------------------------
    def flop_weights(self) -> FlopWeights:
        return FlopWeights.from_abs_flop_costs(
            {
                FlopType.ABS: self.FABS.geo_mean(),
                FlopType.MINUS: self.FNEG.geo_mean(),
                FlopType.EQUALS: self.FCMP.geo_mean(),
                FlopType.GTE: self.FCMP.geo_mean(),
                FlopType.LTE: self.FCMP.geo_mean(),
                FlopType.CMP_ZERO: self.FCMP.geo_mean(),
                FlopType.RND: self.FCVTZS.geo_mean(),
                FlopType.ADD: self.FADD.geo_mean(),
                FlopType.SUB: self.FSUB.geo_mean(),
                FlopType.MUL: self.FMUL.geo_mean(),
                FlopType.DIV: self.FDIV.geo_mean(),
                FlopType.SQRT: self.FSQRT.geo_mean(),
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
