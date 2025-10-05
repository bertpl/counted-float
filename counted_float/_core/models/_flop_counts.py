from __future__ import annotations

import dataclasses

from ._flop_type import FlopType
from ._flop_weights import FlopWeights


@dataclasses.dataclass(slots=True)
class FlopCounts:
    """
    Class to keep track of flop counts per flop type.  The implementation is different from
    the FlopWeights class, for two reasons:
        - there's no need for (de)serialization, hence no usage of Pydantic
        - we want to minimize overhead of flop counting, hence use no dict in favor of explicit fields per flop type
    """

    # --- Counting fields ---------------------------------
    ABS: int = 0
    MINUS: int = 0
    COMP: int = 0
    RND: int = 0
    F2I: int = 0
    I2F: int = 0
    ADD: int = 0
    SUB: int = 0
    MUL: int = 0
    DIV: int = 0
    SQRT: int = 0
    CBRT: int = 0
    EXP: int = 0
    EXP2: int = 0
    EXP10: int = 0
    LOG: int = 0
    LOG2: int = 0
    LOG10: int = 0
    POW: int = 0
    SIN: int = 0
    COS: int = 0
    TAN: int = 0

    # --- math --------------------------------------------
    def __add__(self, other: FlopCounts) -> FlopCounts:
        return FlopCounts(**{attr: getattr(self, attr) + getattr(other, attr) for attr in self.field_names()})

    def __sub__(self, other: FlopCounts) -> FlopCounts:
        return FlopCounts(**{attr: getattr(self, attr) - getattr(other, attr) for attr in self.field_names()})

    # --- extract info ------------------------------------
    def as_dict(self) -> dict[FlopType, int]:
        """Return the flop counts as a dictionary with FlopType keys."""
        return {flop_type: getattr(self, flop_type.name) for flop_type in FlopType}

    def total_count(self) -> int:
        """Sum of all flop counts."""
        return sum(getattr(self, attr) for attr in self.field_names())

    def total_weighted_cost(self, weights: FlopWeights | None = None) -> float:
        """
        Returns a weighted total count of all flops (counterpart of the unweighted total_count() method),
        using the provided weights in the computations.
        When omitted, the currently configured weights (see Config class) will be used.
        """
        if not weights:
            from counted_float._core.counting.config import get_active_flop_weights

            weights = get_active_flop_weights()

        return sum([getattr(self, flop_type.name) * weights.weights[flop_type] for flop_type in FlopType])

    # --- other -------------------------------------------
    def reset(self):
        """Reset all counts to 0"""
        for attr in self.field_names():
            setattr(self, attr, 0)

    def copy(self) -> FlopCounts:
        return FlopCounts(**dataclasses.asdict(self))

    @classmethod
    def field_names(cls) -> list[str]:
        return [field.name for field in dataclasses.fields(cls)]
