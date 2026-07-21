from __future__ import annotations

import dataclasses
from copy import copy as shallow_copy
from typing import TYPE_CHECKING

from ._flop_type import FlopType

if TYPE_CHECKING:
    from ._flop_weights import FlopWeights


@dataclasses.dataclass(slots=True)
class FlopCounts:
    """Class to keep track of flop counts per flop type.

    The implementation is different from the FlopWeights class, for two reasons:
        - there's no need for (de)serialization, hence no usage of Pydantic
        - we want to minimize overhead of flop counting, hence use no dict in favor of explicit fields per flop type.
    """

    # --- Counting fields ---------------------------------
    ABS: int = 0
    MINUS: int = 0
    COPYSIGN: int = 0
    COMP: int = 0
    RND: int = 0
    F2I: int = 0
    I2F: int = 0
    ADD: int = 0
    SUB: int = 0
    MUL: int = 0
    DIV: int = 0
    FMA: int = 0
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
    ASIN: int = 0
    ACOS: int = 0
    ATAN: int = 0
    ATAN2: int = 0
    HYPOT: int = 0
    HYPOT_XARG: int = 0
    EXPM1: int = 0
    LOG1P: int = 0
    FMOD: int = 0
    REMAINDER: int = 0
    SINH: int = 0
    COSH: int = 0
    TANH: int = 0
    ASINH: int = 0
    ACOSH: int = 0
    ATANH: int = 0
    DIST: int = 0
    DIST_XARG: int = 0
    GAMMA: int = 0
    LGAMMA: int = 0
    ERF: int = 0
    ERFC: int = 0

    # --- math --------------------------------------------
    def __add__(self, other: FlopCounts) -> FlopCounts:
        return FlopCounts(**{attr: getattr(self, attr) + getattr(other, attr) for attr in _FIELD_NAMES})

    def __sub__(self, other: FlopCounts) -> FlopCounts:
        # raw element-wise difference: subtracting larger counts yields negative ones, which are
        # meaningless as counts but are how a context derives its own total from two snapshots
        return FlopCounts(**{attr: getattr(self, attr) - getattr(other, attr) for attr in _FIELD_NAMES})

    # --- extract info ------------------------------------
    def as_dict(self) -> dict[FlopType, int]:
        """Return the flop counts as a dictionary with FlopType keys."""
        return {flop_type: getattr(self, flop_type.name) for flop_type in FlopType}

    def total_count(self) -> int:
        """Sum of all flop counts."""
        return sum(getattr(self, attr) for attr in _FIELD_NAMES)

    def total_weighted_cost(self, weights: FlopWeights | None = None) -> float:
        """Return a weighted total count of all flops (counterpart of the unweighted total_count() method).

        Uses the provided weights in the computations.
        When omitted, the currently configured weights (see Config class) will be used.
        """
        if weights is None:
            from counted_float._core.counting.config import get_active_flop_weights

            weights = get_active_flop_weights()

        # zero counts are skipped rather than multiplied: 0 * nan is nan, so a missing (NaN)
        # weight must only affect totals whose counts actually used that flop type
        return sum(
            count * weights.weights[flop_type] for flop_type in FlopType if (count := getattr(self, flop_type.name))
        )

    # --- increment-target contract -----------------------
    def note(self, rationale: str) -> None:
        """No-op counterpart of `FlopCountsWithLogging.note()`: the rationale is dropped.

        Counting sites explain their less obvious decisions unconditionally, so plain counts have
        to accept a rationale too — they simply have nowhere to render it.

        Args:
            rationale: Why the next flop is counted the way it is; unused here.  Keep it a
                constant string: every call builds one, including the calls that discard it.
        """

    # --- other -------------------------------------------
    def reset(self) -> None:
        """Reset all counts to 0."""
        for attr in _FIELD_NAMES:
            setattr(self, attr, 0)

    def copy(self) -> FlopCounts:
        """Return an independent copy of these counts."""
        # every field is an int, so a shallow copy is already independent -- asdict() would walk
        # the deepcopy machinery over them for nothing
        return shallow_copy(self)

    @classmethod
    def field_names(cls) -> list[str]:
        """Return the names of the per-flop-type count fields."""
        return list(_FIELD_NAMES)


# the field names are fixed at class-creation time; resolving them through dataclasses.fields()
# on every call showed up in the reporting path, which reads them once per count readout
_FIELD_NAMES: tuple[str, ...] = tuple(field.name for field in dataclasses.fields(FlopCounts))
