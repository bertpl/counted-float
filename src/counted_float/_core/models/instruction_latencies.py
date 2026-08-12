from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import Field

from .base import JsonReprModel
from .flop_type import FlopType
from .flop_weights import FlopWeights


# =================================================================================================
#  Single-Instruction Latency
# =================================================================================================
class Latency(JsonReprModel):
    note: str = ""
    min_cycles: float | None = None
    max_cycles: float | None = None

    def consensus(self) -> float:
        """Calculate the consensus value of min/max cycles.

        max(min_cycles, max_cycles) correlates best with benchmarks.
        This always either returns a value > 0 or math.nan (if both min_cycles and max_cycles are None).
        """
        match (self.min_cycles, self.max_cycles):
            case (None, None):
                return math.nan
            case (None, _):
                return max(1.0, self.max_cycles)  # ty: ignore[invalid-argument-type] -- non-None here
            case (_, None):
                return max(1.0, self.min_cycles)  # ty: ignore[invalid-argument-type] -- non-None per pattern
            case (_, _):
                return max(1.0, self.min_cycles, self.max_cycles)  # ty: ignore[invalid-argument-type] -- non-None


# =================================================================================================
#  InstructionLatencies - SSE2
# =================================================================================================
class InstructionLatencies_SSE2(JsonReprModel):  # noqa: N801 -- established public API name
    """Latencies of the x86 instructions a modern compiler emits for scalar double-precision math.

    The `sse2` tag distinguishes this from the ancient x87 FPU, rather than asserting that every
    instruction below belongs to the SSE2 extension: it names the modern scalar x86 baseline, and
    each field is whatever the current best instruction for that operation is. ROUNDSD (SSE4.1)
    and VFMADD213SD (FMA3) are both here for that reason.
    """

    # --- primary fields ----------------------------------
    architecture: Literal["sse2"] = "sse2"

    ANDPD: Latency = Latency()  # abs(x)
    ROUNDSD: Latency = Latency()  # round        (float -> float)
    CVTSD2SI: Latency = Latency()  # double -> int
    CVTSI2SD: Latency = Latency()  # int -> double
    XORPD: Latency = Latency()  # -x
    UCOMISD: Latency = Latency()  # x < == > y, x < == > 0
    MAXSD: Latency = Latency()  # max(x,y)
    MINSD: Latency = Latency()  # min(x,y)
    ADDSD: Latency = Latency()  # x+y
    SUBSD: Latency = Latency()  # x-y
    MULSD: Latency = Latency()  # x*y
    DIVSD: Latency = Latency()  # x/y
    VFMADD213SD: Latency = Latency()  # x*y+z, fused
    SQRTSD: Latency = Latency()  # sqrt(x)

    # --- helpers -----------------------------------------
    def flop_weights(self) -> FlopWeights:
        return FlopWeights.from_abs_flop_costs(
            {
                FlopType.ABS: self.ANDPD.consensus(),
                FlopType.MINUS: self.XORPD.consensus(),
                FlopType.COMP: self.UCOMISD.consensus(),
                FlopType.RND: self.ROUNDSD.consensus(),
                FlopType.F2I: self.CVTSD2SI.consensus(),
                FlopType.I2F: self.CVTSI2SD.consensus(),
                FlopType.ADD: self.ADDSD.consensus(),
                FlopType.SUB: self.SUBSD.consensus(),
                FlopType.MUL: self.MULSD.consensus(),
                FlopType.DIV: self.DIVSD.consensus(),
                FlopType.FMA: self.VFMADD213SD.consensus(),
                FlopType.SQRT: self.SQRTSD.consensus(),
            }
        )


# =================================================================================================
#  InstructionLatencies - ARM
# =================================================================================================
class InstructionLatencies_ARM(JsonReprModel):  # noqa: N801 -- established public API name
    # --- primary fields ----------------------------------
    architecture: Literal["arm"] = "arm"

    FABS: Latency = Latency()  # abs(x)
    FRINT: Latency = Latency()  # round        (float -> float)
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
    FMADD: Latency = Latency()  # x*y+z, fused
    FSQRT: Latency = Latency()  # sqrt(x)

    # --- helpers -----------------------------------------
    def flop_weights(self) -> FlopWeights:
        return FlopWeights.from_abs_flop_costs(
            {
                FlopType.ABS: self.FABS.consensus(),
                FlopType.MINUS: self.FNEG.consensus(),
                FlopType.COMP: self.FCMP.consensus(),
                FlopType.RND: self.FRINT.consensus(),
                FlopType.F2I: self.FCVTZS.consensus(),
                FlopType.I2F: self.SCVTF.consensus(),
                FlopType.ADD: self.FADD.consensus(),
                FlopType.SUB: self.FSUB.consensus(),
                FlopType.MUL: self.FMUL.consensus(),
                FlopType.DIV: self.FDIV.consensus(),
                FlopType.FMA: self.FMADD.consensus(),
                FlopType.SQRT: self.FSQRT.consensus(),
            }
        )


# =================================================================================================
#  Union Class
# =================================================================================================
class InstructionLatencies(JsonReprModel):
    notes: list[str] | None = [""]  # noqa: RUF012 -- pydantic deep-copies field defaults per instance
    latencies: Annotated[
        InstructionLatencies_SSE2 | InstructionLatencies_ARM,
        Field(discriminator="architecture"),
    ]

    def flop_weights(self) -> FlopWeights:
        return self.latencies.flop_weights()
