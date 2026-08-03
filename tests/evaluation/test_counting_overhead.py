import warnings

import pytest

from counted_float._core.counting import CountedFloat, FlopCountingContext
from counted_float._core.evaluation import (
    CountedFloatBisection,
    CountingOverheadResults,
    ExcludedFlopType,
    FloatBisection,
    PerFlopTypeOverhead,
    evaluate_counting_overhead,
)
from counted_float._core.evaluation._practical_workload import _zero_function
from counted_float._core.models import FlopType

# golden output for the show() test below; module-level so the wide table rows stay unindented
_EXPECTED_SHOW_OUTPUT = """\
Counting overhead per flop type (CountedFloat vs float, generic counting path):
  FlopType.ADD            [x+y]             x + y                       :     10.00 ns ->     40.00 ns  =     4.0x
  FlopType.GAMMA          [gamma(x)]        math.gamma(x)               :     32.00 ns ->    144.00 ns  =     4.5x

Not measured:
  FlopType.DIST_XARG      [dist(+arg)]      cost increment, not standalone

Geomean overhead across measured flop types: 4.2x

Practical workload: test workload
  float        :    1.00 µs / execution
  CountedFloat :    9.30 µs / execution

CountedFloat is 9.3x slower than float on this workload
"""


def test_evaluate_counting_overhead():
    # Rudimentary test to check the benchmark runs without errors
    result = evaluate_counting_overhead(t_target_sec=0.001)
    result.show()


def test_counted_bisection_registers_the_expected_operation_mix():
    # one bisection over [2, 100] runs N halvings; per zero-function call (N+2: fa, fb, then one
    # per iteration) it counts LGAMMA + SUB, per midpoint ADD + MUL, per while-check SUB + COMP
    # (N+1 checks), and per sign test COMP (N) -- so the relations below hold for any N, and the
    # N-range pins that the bracket/tolerance produce a real bisection rather than a degenerate one
    # --- arrange ----------------------
    benchmark = CountedFloatBisection()
    benchmark._prepare_benchmark(1)

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        benchmark._run_benchmark()
    counts = ctx.flop_counts()
    n_iterations = counts.ADD

    # --- assert -----------------------
    assert 40 <= n_iterations <= 60
    assert n_iterations == counts.MUL
    assert n_iterations + 2 == counts.LGAMMA
    assert 2 * n_iterations + 3 == counts.SUB
    assert 2 * n_iterations + 1 == counts.COMP


def test_float_bisection_registers_nothing():
    # --- arrange ----------------------
    benchmark = FloatBisection()
    benchmark._prepare_benchmark(1)

    # --- act --------------------------
    with FlopCountingContext() as ctx:
        benchmark._run_benchmark()

    # --- assert -----------------------
    assert sum(getattr(ctx.flop_counts(), flop_type.name) for flop_type in FlopType) == 0


def test_show_prints_the_full_report(capsys):
    # --- arrange ----------------------
    results = CountingOverheadResults(
        per_flop_type=[
            PerFlopTypeOverhead(
                flop_type=FlopType.ADD, expression="x + y", float_time_nsec=10.0, counted_float_time_nsec=40.0
            ),
            PerFlopTypeOverhead(
                flop_type=FlopType.GAMMA,
                expression="math.gamma(x)",
                float_time_nsec=32.0,
                counted_float_time_nsec=144.0,
            ),
        ],
        excluded_flop_types=[ExcludedFlopType(flop_type=FlopType.DIST_XARG, reason="cost increment, not standalone")],
        practical_workload_label="test workload",
        float_time_nsec=1000.0,
        counted_float_time_nsec=9300.0,
    )

    # --- act --------------------------
    results.show()

    # --- assert -----------------------
    assert capsys.readouterr().out == _EXPECTED_SHOW_OUTPUT


def test_practical_zero_function_mixes_lgamma_and_operator_work():
    # --- act --------------------------
    with FlopCountingContext() as ctx:
        _zero_function(CountedFloat(3.7))
    counts = ctx.flop_counts()

    # --- assert -----------------------
    assert counts.LGAMMA == 1
    assert counts.SUB == 1


def test_geomean_overhead_ratio_is_the_geometric_mean_of_the_rows():
    # --- arrange ----------------------
    results = CountingOverheadResults(
        per_flop_type=[
            PerFlopTypeOverhead(
                flop_type=FlopType.ADD, expression="x + y", float_time_nsec=10.0, counted_float_time_nsec=40.0
            ),
            PerFlopTypeOverhead(
                flop_type=FlopType.MUL, expression="x * y", float_time_nsec=10.0, counted_float_time_nsec=90.0
            ),
        ],
        excluded_flop_types=[],
        practical_workload_label="test workload",
        float_time_nsec=10.0,
        counted_float_time_nsec=60.0,
    )

    # --- act / assert -----------------
    assert results.geomean_overhead_ratio() == pytest.approx(6.0)  # sqrt(4x * 9x)
    assert results.practical_overhead_ratio() == pytest.approx(6.0)


def test_run_counted_float_benchmark_verbose_false_is_silent(capsys):
    # --- act --------------------------
    evaluate_counting_overhead(t_target_sec=0.001, verbose=False)

    # --- assert -----------------------
    assert capsys.readouterr().out == ""


# =================================================================================================
#  the deprecated home
# =================================================================================================
def test_the_old_benchmarking_name_still_resolves_to_the_moved_function(monkeypatch):
    # what keeps this a minor version: an existing import line must not stop working
    # --- arrange -----------------------------------------
    import counted_float.benchmarking as public_benchmarking

    # the alias binds itself on first use so it warns once per process; drop that binding so this
    # test sees the warning regardless of whether something earlier in the session already tripped it
    monkeypatch.delattr(public_benchmarking, "run_counted_float_benchmark", raising=False)

    # --- act ---------------------------------------------
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        alias = public_benchmarking.run_counted_float_benchmark

    # --- assert ------------------------------------------
    assert alias is evaluate_counting_overhead
    assert [w.category for w in caught] == [DeprecationWarning]
    assert "counted_float.evaluation" in str(caught[0].message)


def test_an_unknown_name_on_the_public_benchmarking_module_still_raises():
    # the alias hook must not swallow every miss
    # --- act / assert ------------------------------------
    import counted_float.benchmarking as public_benchmarking

    with pytest.raises(AttributeError, match="NoSuchThing"):
        _ = public_benchmarking.NoSuchThing
