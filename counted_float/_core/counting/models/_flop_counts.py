from __future__ import annotations

import dataclasses

from ._flop_type import FlopType


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
    EQUALS: int = 0
    GTE: int = 0
    LTE: int = 0
    CMP_ZERO: int = 0
    RND: int = 0
    ADD: int = 0
    SUB: int = 0
    MUL: int = 0
    DIV: int = 0
    SQRT: int = 0
    POW2: int = 0
    LOG2: int = 0
    POW: int = 0

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
