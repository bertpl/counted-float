import pytest

from counted_float._core.models import MicroBenchmarkResult, Quantiles, SingleRunResult


# =================================================================================================
#  Quantiles
# =================================================================================================
@pytest.mark.parametrize(
    ("q25", "q50", "q75", "expected"),
    [
        (90.0, 100.0, 110.0, " ± 10.0%"),
        (0.0, 0.0, 0.0, ""),  # all runs measured zero -> no meaningful percentage, no dangling ±
        (0.0, 0.0, 10.0, ""),  # zero median with nonzero spread must not divide by zero
    ],
)
def test_format_uncertainty_suffix(q25: float, q50: float, q75: float, expected: str):
    # --- arrange -----------------------------------------
    quantiles = Quantiles(q25=q25, q50=q50, q75=q75)

    # --- act / assert ------------------------------------
    assert quantiles.format_uncertainty_suffix() == expected


# =================================================================================================
#  SingleRunResult
# =================================================================================================
def test_single_run_result():
    # --- arrange -----------------------------------------
    srr = SingleRunResult(
        n_executions=10,
        t_nsecs=1234,
        t_cycles=4567,
    )

    # --- act & assert ------------------------------------
    assert srr.nsecs_per_exec() == pytest.approx(123.4, rel=1e-15)
    assert srr.cycles_per_exec() == pytest.approx(456.7, rel=1e-15)


# =================================================================================================
#  MicroBenchmarkResult
# =================================================================================================
def test_micro_benchmark_result():
    # --- arrange -----------------------------------------
    mbr = MicroBenchmarkResult(
        warmup_runs=[],
        benchmark_runs=[
            SingleRunResult(
                n_executions=10,
                t_nsecs=1.0 + i,  # 1.0 -> 11.0
                t_cycles=2.0 + i,  # 2.0 -> 12.0
            )
            for i in range(11)
        ],
    )

    # --- act & assert ------------------------------------
    assert mbr.summary_stats_nsecs_per_exec().q25 == pytest.approx(0.35, rel=1e-15)
    assert mbr.summary_stats_nsecs_per_exec().q50 == pytest.approx(0.60, rel=1e-15)
    assert mbr.summary_stats_nsecs_per_exec().q75 == pytest.approx(0.85, rel=1e-15)
    assert mbr.summary_stats_cycles_per_exec().q25 == pytest.approx(0.45, rel=1e-15)
    assert mbr.summary_stats_cycles_per_exec().q50 == pytest.approx(0.70, rel=1e-15)
    assert mbr.summary_stats_cycles_per_exec().q75 == pytest.approx(0.95, rel=1e-15)
