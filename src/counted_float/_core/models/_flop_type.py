from __future__ import annotations

import math
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pydantic import FieldSerializationInfo

_V = TypeVar("_V")


class FlopType(StrEnum):
    """Enum describing the different types of floating-point operations.

    Each of these is counted separately and can potentially have a different weight.
    --> See: /docs/analysis_methodology.md.

    The member *value* is a stable identifier equal to the member name (e.g. ``"ADD"``); it is
    what serializes as the JSON key of every weight file, so it must not change once shipped. The
    human-readable label (``"x+y"``) is a separate presentation concern -- see ``label``.
    """

    ABS = "ABS"
    MINUS = "MINUS"
    COPYSIGN = "COPYSIGN"
    COMP = "COMP"
    RND = "RND"
    F2I = "F2I"
    I2F = "I2F"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    FMA = "FMA"
    SQRT = "SQRT"
    CBRT = "CBRT"
    EXP = "EXP"
    EXP2 = "EXP2"
    EXP10 = "EXP10"
    LOG = "LOG"
    LOG2 = "LOG2"
    LOG10 = "LOG10"
    POW = "POW"
    SIN = "SIN"
    COS = "COS"
    TAN = "TAN"
    ASIN = "ASIN"
    ACOS = "ACOS"
    ATAN = "ATAN"
    ATAN2 = "ATAN2"
    HYPOT = "HYPOT"
    EXPM1 = "EXPM1"
    LOG1P = "LOG1P"
    FMOD = "FMOD"
    SINH = "SINH"
    COSH = "COSH"
    TANH = "TANH"
    ASINH = "ASINH"
    ACOSH = "ACOSH"
    ATANH = "ATANH"

    @property
    def label(self) -> str:
        """Human-readable display label (e.g. ``"x+y"``), decoupled from the on-disk key."""
        return _LABELS[self]

    def long_name(self) -> str:
        """Return a display string combining the stable name and the human-readable label."""
        return f"FlopType.{self.name:<9}  [{self.label}]"

    @classmethod
    def from_serialized_key(cls, key: str) -> FlopType:
        """Resolve a serialized weight-dict key (a stable member name) to its member.

        Raises:
            ValueError: If the key is not a FlopType name -- a loud failure, rather than
                silently degrading into a missing (NaN) weight. Pre-2.0.0 files keyed on
                display labels; those are no longer readable and must be regenerated.
        """
        try:
            return cls[key]
        except KeyError:
            raise ValueError(f"unrecognized flop-type key {key!r}: not a FlopType name") from None


# =================================================================================================
#  Display labels + serialized-key handling
# =================================================================================================
# The label is the human-facing spelling; it may change freely without touching any on-disk file,
# because the JSON key is the stable name (member value) instead.
_LABELS: dict[FlopType, str] = {
    FlopType.ABS: "abs(x)",
    FlopType.MINUS: "-x",
    FlopType.COPYSIGN: "copysign(x,y)",
    FlopType.COMP: "x<=y",
    FlopType.RND: "round",
    FlopType.F2I: "float->int",
    FlopType.I2F: "int->float",
    FlopType.ADD: "x+y",
    FlopType.SUB: "x-y",
    FlopType.MUL: "x*y",
    FlopType.DIV: "x/y",
    FlopType.FMA: "x*y+z",
    FlopType.SQRT: "sqrt(x)",
    FlopType.CBRT: "cbrt(x)",
    FlopType.EXP: "e^x",
    FlopType.EXP2: "2^x",
    FlopType.EXP10: "10^x",
    FlopType.LOG: "log(x)",
    FlopType.LOG2: "log2(x)",
    FlopType.LOG10: "log10(x)",
    FlopType.POW: "x^y",
    FlopType.SIN: "sin(x)",
    FlopType.COS: "cos(x)",
    FlopType.TAN: "tan(x)",
    FlopType.ASIN: "asin(x)",
    FlopType.ACOS: "acos(x)",
    FlopType.ATAN: "atan(x)",
    FlopType.ATAN2: "atan2(y,x)",
    FlopType.HYPOT: "hypot(x,y)",
    FlopType.EXPM1: "expm1(x)",
    FlopType.LOG1P: "log1p(x)",
    FlopType.FMOD: "fmod(x,y)",
    FlopType.SINH: "sinh(x)",
    FlopType.COSH: "cosh(x)",
    FlopType.TANH: "tanh(x)",
    FlopType.ASINH: "asinh(x)",
    FlopType.ACOSH: "acosh(x)",
    FlopType.ATANH: "atanh(x)",
}


def normalize_flop_type_keyed_dict(v: object, *, null_to_nan: bool) -> object:
    """Resolve the string keys of a serialized FlopType-keyed dict to members.

    Shared by the ``mode="before"`` validators of every model that stores a ``dict[FlopType, ...]``.
    Unrecognized keys raise (via ``from_serialized_key``); already-resolved ``FlopType`` keys pass
    through. Non-dict input is returned untouched so pydantic can raise its own type error.

    Args:
        v: The raw validator input -- a dict with string (or already-resolved member) keys when it
            comes from JSON; anything else is passed through untouched.
        null_to_nan: When True, a JSON ``null`` value becomes ``math.nan`` -- how the weight
            models mark missing data. Latency-style dicts pass False (no missing markers).
    """
    if not isinstance(v, dict):
        return v
    resolved: dict[FlopType, object] = {}
    for key, value in v.items():
        member = key if isinstance(key, FlopType) else FlopType.from_serialized_key(str(key))
        resolved[member] = math.nan if (null_to_nan and value is None) else value
    return resolved


def serialize_flop_type_keyed_dict(d: Mapping[FlopType, _V], info: FieldSerializationInfo) -> dict[str, _V]:
    """Serialize a FlopType-keyed dict, keying on the stable name by default.

    A ``{"display": True}`` serialization context switches the keys to the human-readable labels,
    which is what the pretty ``__str__`` / ``show()`` paths pass. On-disk writes pass no context,
    so files always carry the stable names.
    """
    display = bool((info.context or {}).get("display"))
    return {(flop_type.label if display else flop_type.name): value for flop_type, value in d.items()}
