from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import field_serializer, field_validator

from .base import JsonReprModel
from .flop_type import FlopType, normalize_flop_type_keyed_dict, serialize_flop_type_keyed_dict
from .flop_weights import FlopWeights
from .flops_benchmark_meta_data import BenchmarkSettings, SystemInfo
from .flops_benchmark_type import FlopsBenchmarkType
from .micro_benchmark_result import Quantiles

if TYPE_CHECKING:
    from pydantic import FieldSerializationInfo


# =================================================================================================
#  Main Flops Benchmark Information
# =================================================================================================
class FlopsBenchmarkResults(JsonReprModel):
    # --- meta-data ---
    system: SystemInfo
    benchmark_settings: BenchmarkSettings

    # --- results ---
    n_cycles_per_op: dict[FlopsBenchmarkType, Quantiles]  # number of cpu cycles per element in array
    estimated_flop_latencies: dict[FlopType, float]  # number of cpu cycles per flop type

    # --- serialization: same stable-name key handling as FlopWeights ---
    @field_validator("estimated_flop_latencies", mode="before")
    @classmethod
    def normalize_latency_keys(cls, v: object) -> object:
        """Resolve serialized keys (stable member names) to members; unknown keys raise."""
        return normalize_flop_type_keyed_dict(v, null_to_nan=False)

    @field_serializer("estimated_flop_latencies")
    def serialize_latencies(self, latencies: dict[FlopType, float], info: FieldSerializationInfo) -> dict[str, float]:
        # stable names on disk; human labels only under a {"display": True} context
        return serialize_flop_type_keyed_dict(latencies, info)

    # --- helpers ---
    def flop_weights(self) -> FlopWeights:
        """Returns normalized weights for each flop type based on the benchmark results."""
        return FlopWeights.from_abs_flop_costs(self.estimated_flop_latencies)
