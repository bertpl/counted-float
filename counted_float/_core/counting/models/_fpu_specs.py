from __future__ import annotations

import math

from pydantic import field_validator

from . import FlopType
from ._base import MyBaseModel
from ._flop_weights import FlopWeights
from ._fpu_instruction import FPUInstruction


class Latency(MyBaseModel):
    min_cycles: int
    max_cycles: int

    def geo_mean(self) -> float:
        """Calculate the geometric mean of min and max cycles."""
        return math.sqrt(self.min_cycles * self.max_cycles)


class InstructionLatencies(MyBaseModel):
    """Provides FPU instruction latency (in min/max processor cycles) per flop type."""

    latencies: dict[FPUInstruction, Latency]

    # -------------------------------------------------------------------------
    #  Helpers
    # -------------------------------------------------------------------------
    @property
    def flop_weights(self) -> FlopWeights:
        """
        Calculates estimated flop weights based on instruction latencies.

        Note that some FPU instructions (e.g. FCOM) correspond to multiple flop types and some flop types (e.g. a^b)
        consist of multiple FPU instructions.

        Background:
          - [FIL] "Simply FPU", by Raymond Filiatreault, available at: https://masm32.com/masmcode/rayfil/tutorial/index.html

        | Math operation              | FPU instruction              | Comment               |
        |-----------------------------|------------------------------|-----------------------|
        | abs(a)                      | `FABS`                       |                       |
        | -a                          | `FCHS`                       |                       |
        | a==b, a>=b, a>b             | `FCOM`                       |                       |
        | a>0, a>=0, a==0             | `FTST`                       |                       |
        | round(a), floor(a), ceil(a) | `FRNDINT`                    | See [FIL], chapter 8  |
        | a+b                         | `FADD`                       |                       |
        | a-b                         | `FSUB`                       |                       |
        | a*b                         | `FMUL`                       |                       |
        | a/b                         | `FDIV`                       |                       |
        | sqrt(a)                     | `FSQRT`                      |                       |
        | log2(a)                     | `FYL2X`                      |                       |
        | 2^a                         | > `F2XM1`                    | See [FIL], chapter 11 |
        | a^b                         | > `FYL2X` + `F2XM1` + `FMUL` | See [FIL], chapter 11 |
        """

        # step 1) take geo_mean of all instruction latencies
        lat = {k: v.geo_mean() for k, v in self.latencies.items()}

        # step 2) convert instruction latencies to estimated flop costs
        I = FPUInstruction
        est_flop_type_latencies = {
            FlopType.ABS: lat[I.FABS],
            FlopType.MINUS: lat[I.FCHS],
            FlopType.EQUALS: lat[I.FCOM],
            FlopType.GTE: lat[I.FCOM],
            FlopType.LTE: lat[I.FCOM],
            FlopType.CMP_ZERO: lat[I.FTST],
            FlopType.RND: lat[I.FRNDINT],
            FlopType.ADD: lat[I.FADD],
            FlopType.SUB: lat[I.FSUB],
            FlopType.MUL: lat[I.FMUL],
            FlopType.DIV: lat[I.FDIV],
            FlopType.SQRT: lat[I.FSQRT],
            FlopType.POW2: lat[I.F2XM1],
            FlopType.LOG2: lat[I.FYL2X],
            FlopType.POW: lat[I.F2XM1] + lat[I.FYL2X] + lat[I.FMUL],  # a^b = 2^(b*log2(a))
        }

        # step 3) convert to normalized FlopWeights by using a few simple flop types as reference (see FlopWeights)
        return FlopWeights.from_abs_flop_costs(est_flop_type_latencies)

    # -------------------------------------------------------------------------
    #  Validation
    # -------------------------------------------------------------------------
    @field_validator("latencies")
    @classmethod
    def check_all_instructions_present(cls, v: dict[FPUInstruction, Latency]) -> dict[FPUInstruction, Latency]:
        # make sure all FPUInstruction enum members are present
        missing = [member for member in FPUInstruction if member not in v]
        if missing:
            raise ValueError(f"Missing latencies for FPU instructions: {missing}")
        return v
