"""Result models for the counting-overhead evaluation: per-type rows, exclusions, and the report."""

import math
from statistics import fmean

from counted_float._core.models import FlopType, JsonReprModel
from counted_float._core.utils import format_time_duration


# =================================================================================================
#  Per-flop-type rows
# =================================================================================================
class PerFlopTypeOverhead(JsonReprModel):
    """Measured counting overhead of one flop type, on its generic counting path.

    Times are per operation and include the timed loop's per-iteration scaffolding, which is
    identical in both variants; expression is the measured spelling as the loop runs it.
    """

    flop_type: FlopType
    expression: str
    float_time_nsec: float
    counted_float_time_nsec: float

    def overhead_ratio(self) -> float:
        """How many times slower the counted operation is than its plain-float baseline."""
        return self.counted_float_time_nsec / self.float_time_nsec


class ExcludedFlopType(JsonReprModel):
    """A flop type without a per-type overhead row, and the measurement reason it is excluded."""

    flop_type: FlopType
    reason: str


# =================================================================================================
#  The full report
# =================================================================================================
class CountingOverheadResults(JsonReprModel):
    """The counting-overhead report: per-flop-type rows, exclusions, and the practical workload.

    float_time_nsec and counted_float_time_nsec are the practical workload's per-execution
    timings; practical_workload_label states what that workload computes.
    """

    per_flop_type: list[PerFlopTypeOverhead]
    excluded_flop_types: list[ExcludedFlopType]
    practical_workload_label: str
    float_time_nsec: float
    counted_float_time_nsec: float

    def geomean_overhead_ratio(self) -> float:
        """Geometric mean of the per-type overhead ratios, over the measured types only."""
        return math.exp(fmean(math.log(row.overhead_ratio()) for row in self.per_flop_type))

    def practical_overhead_ratio(self) -> float:
        """How many times slower the practical workload runs counted than on plain floats."""
        return self.counted_float_time_nsec / self.float_time_nsec

    def show(self) -> None:
        """Print the report: per-type table, exclusions, geomean, and the practical workload."""
        # long_name() pads its name column, but its label suffix varies in width; padding the
        # whole string keeps the columns after it aligned
        name_width = max(len(flop_type.long_name()) for flop_type in FlopType)
        print("Counting overhead per flop type (CountedFloat vs float, generic counting path):")
        for row in self.per_flop_type:
            t_float = format_time_duration(row.float_time_nsec)
            t_counted = format_time_duration(row.counted_float_time_nsec)
            print(
                f"  {row.flop_type.long_name():<{name_width}}  {row.expression:<28}: "
                f"{t_float:>12} -> {t_counted:>12}  = {row.overhead_ratio():7.1f}x"
            )
        if self.excluded_flop_types:
            print()
            print("Not measured:")
            for excluded in self.excluded_flop_types:
                print(f"  {excluded.flop_type.long_name():<{name_width}}  {excluded.reason}")
        print()
        print(f"Geomean overhead across measured flop types: {self.geomean_overhead_ratio():.1f}x")
        print()
        print(f"Practical workload: {self.practical_workload_label}")
        print(f"  float        : {format_time_duration(self.float_time_nsec)} / execution")
        print(f"  CountedFloat : {format_time_duration(self.counted_float_time_nsec)} / execution")
        print()
        print(f"CountedFloat is {self.practical_overhead_ratio():.1f}x slower than float on this workload")
