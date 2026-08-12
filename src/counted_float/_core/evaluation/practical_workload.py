"""The practical mixed workload: a bisection whose zero function does lgamma work.

The per-flop-type loops state the overhead range's endpoints; this workload shows where a
realistic mix lands inside it. Each bisection iteration combines the machinery's cheap operator
work (add, multiply, subtract, comparisons) with one expensive patched-math call per function
evaluation, so neither regime dominates by construction.

lgamma is the expensive ingredient rather than gamma because it is monotonic for x >= 2 (so the
bracket below always straddles exactly one root) and never overflows on the bracket, where
gamma(x) already overflows for moderate x.
"""

import math

from counted_float._core.counting import CountedFloat, FlopCountingContext
from counted_float._core.micro_benchmarking import MicroBenchmark

# Bracket and target: lgamma(2) = 0 and lgamma(100) ~ 359, so lgamma(x) - target has exactly one
# root inside the bracket, and the bisection runs its full course for any tolerance
_BRACKET_LO = 2.0
_BRACKET_HI = 100.0
_LGAMMA_TARGET = 10.0

# What the report calls this workload, derived from the constants so the label cannot drift
PRACTICAL_WORKLOAD_LABEL = f"bisection of lgamma(x) - {_LGAMMA_TARGET} on [{_BRACKET_LO}, {_BRACKET_HI}]"


def _zero_function(x: float) -> float:
    """The function whose root the bisection hunts: one lgamma call plus one subtract."""
    return math.lgamma(x) - _LGAMMA_TARGET


class FloatBisection(MicroBenchmark):
    """The practical workload on plain floats."""

    def __init__(self) -> None:
        """Create the float variant."""
        super().__init__(name="float")
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int) -> None:
        """Store the execution count for the next timed run."""
        self._n_executions = n_executions

    def _run_benchmark(self) -> None:
        """Run n_executions bisections of _zero_function over the bracket."""
        for _ in range(self._n_executions):
            a = _BRACKET_LO
            b = _BRACKET_HI
            # NOTE: fa/fb are never read (the loop re-evaluates fmid instead); they are kept
            #       on purpose so the probe mimics a realistic bisection workload
            fa = _zero_function(a)
            fb = _zero_function(b)
            while b - a > 1e-12:
                mid = 0.5 * (a + b)
                fmid = _zero_function(mid)
                if fmid < 0:
                    a = mid
                    fa = fmid  # noqa: F841
                else:
                    b = mid
                    fb = fmid  # noqa: F841


class CountedFloatBisection(MicroBenchmark):
    """The practical workload on CountedFloat, counted inside an open FlopCountingContext.

    The context is required, not a convenience: math.lgamma is only patched -- and the zero
    function's call only counted and type-preserving -- while one is open. It is entered inside
    the timed region, where its fixed patch/unpatch cost amortizes over the run's target duration.
    """

    def __init__(self) -> None:
        """Create the CountedFloat variant."""
        super().__init__(name="CountedFloat")
        self._n_executions = 1

    def _prepare_benchmark(self, n_executions: int) -> None:
        """Store the execution count for the next timed run."""
        self._n_executions = n_executions

    def _run_benchmark(self) -> None:
        """Run n_executions bisections, identical to FloatBisection except for the wrapped bracket.

        Initializing a and b as CountedFloat makes every downstream operation counted arithmetic.
        """
        with FlopCountingContext():
            for _ in range(self._n_executions):
                a = CountedFloat(_BRACKET_LO)
                b = CountedFloat(_BRACKET_HI)
                # NOTE: fa/fb are never read (the loop re-evaluates fmid instead); they are kept
                #       on purpose so the probe mimics a realistic bisection workload
                fa = _zero_function(a)
                fb = _zero_function(b)
                while b - a > 1e-12:
                    mid = 0.5 * (a + b)
                    fmid = _zero_function(mid)
                    if fmid < 0:
                        a = mid
                        fa = fmid  # noqa: F841
                    else:
                        b = mid
                        fb = fmid  # noqa: F841
