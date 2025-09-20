from __future__ import annotations

import math
from typing import Annotated, Literal, Union

from pydantic import Field

from ._base import MyBaseModel
from ._flop_type import FlopType
from ._flop_weights import FlopWeights


# =================================================================================================
#  Single-Instruction Latency
# =================================================================================================
class Latency(MyBaseModel):
    min_cycles: float
    max_cycles: float

    def geo_mean(self) -> float:
        """Calculate the geometric mean of min and max cycles."""
        return math.sqrt(self.min_cycles * self.max_cycles)


# =================================================================================================
#  InstructionLatencies - x87
# =================================================================================================
class InstructionLatencies_x87(MyBaseModel):
    # SEE: https://github.com/bertpl/counted-float/tree/develop/counted_float/data/fpu_data_sources.md

    # --- primary fields ----------------------------------
    architecture: Literal["x87"] = "x87"

    FABS: Latency | None = None  # abs(x)
    FCHS: Latency | None = None  # -x
    FCOM: Latency | None = None  # x < == > y
    FTST: Latency | None = None  # x < == > 0
    FRNDINT: Latency | None = None  # double -> int
    FADD: Latency | None = None  # x+y
    FSUB: Latency | None = None  # x-y
    FMUL: Latency | None = None  # x*y
    FDIV: Latency | None = None  # x/y
    FSQRT: Latency | None = None  # sqrt(x)
    F2XM1: Latency | None = None  # 2 raised to the power of float minus 1 (2**a - 1)
    FYL2X: Latency | None = None  # logarithm base 2 of float (log2(a))

    # --- helpers -----------------------------------------
    def flop_weights(self) -> FlopWeights:
        return FlopWeights.from_abs_flop_costs(
            {
                FlopType.ABS: _geo_mean_latency(self.FABS),
                FlopType.MINUS: _geo_mean_latency(self.FCHS),
                FlopType.EQUALS: _geo_mean_latency(self.FCOM),
                FlopType.GTE: _geo_mean_latency(self.FCOM),
                FlopType.LTE: _geo_mean_latency(self.FCOM),
                FlopType.CMP_ZERO: _geo_mean_latency(self.FTST),
                FlopType.RND: _geo_mean_latency(self.FRNDINT),
                FlopType.ADD: _geo_mean_latency(self.FADD),
                FlopType.SUB: _geo_mean_latency(self.FSUB),
                FlopType.MUL: _geo_mean_latency(self.FMUL),
                FlopType.DIV: _geo_mean_latency(self.FDIV),
                FlopType.SQRT: _geo_mean_latency(self.FSQRT),
                FlopType.POW2: _geo_mean_latency(self.F2XM1),
                FlopType.LOG2: _geo_mean_latency(self.FYL2X),
                FlopType.POW: (
                    _geo_mean_latency(self.F2XM1) + _geo_mean_latency(self.FYL2X) + _geo_mean_latency(self.FMUL)
                ),  # a^b = 2^(b*log2(a))
            }
        )


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
            InstructionLatencies_x87,
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
