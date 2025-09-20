from __future__ import annotations

import math

from pydantic import field_validator

from counted_float._core.models._base import MyBaseModel
from counted_float._core.models._flop_type import FlopType
from counted_float._core.models._flop_weights import FlopWeights
from counted_float._core.models._instruction_latencies import Latency

from ._fpu_instruction_x87 import FPUInstruction_x87


class InstructionLatencies_x87(MyBaseModel):
    """Provides FPU instruction latency (in min/max processor cycles) per flop type."""

    notes: list[str] | None = [""]
    latencies: dict[FPUInstruction_x87, Latency | None]

    # -------------------------------------------------------------------------
    #  Helpers
    # -------------------------------------------------------------------------
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
        | a==b, a>=b, a>b             | `FCOM`                       | See Note (1)          |
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

        NOTE 1:  FCOM should be assigned the range of values found for FCOM, FCOMI, FCOMIP, FCOMP & FCOMPP instructions
        """

        # step 1) take geo_mean of all instruction latencies
        #         (or math.nan for missing data; FlopWeights will interpret as missing data)
        lat = {k: math.nan if v is None else v.geo_mean() for k, v in self.latencies.items()}

        # step 2) convert instruction latencies to estimated flop costs
        I = FPUInstruction_x87
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
    def check_all_instructions_present(
        cls, v: dict[FPUInstruction_x87, Latency | None]
    ) -> dict[FPUInstruction_x87, Latency | None]:
        # ensure all FPUInstruction enum members are present
        for member in FPUInstruction_x87:
            if member not in v:
                v[member] = None
        return v
