import time

import pytest

from counted_float._core.benchmarking._time_utils import (
    Timer,
    _format_nsec_as_ms,
    _format_nsec_as_ns,
    _format_nsec_as_s,
    _format_nsec_as_us,
    format_time_durations,
)


# =================================================================================================
#  Formatting utils
# =================================================================================================
@pytest.mark.parametrize(
    "nsec, expected_result",
    [
        (6.55003, "   6.55 ns"),
        (12.33002, "  12.33 ns"),
        (345.11001, " 345.11 ns"),
        (1999.7799, "1999.78 ns"),
    ],
)
def test_format_nsec_as_ns(nsec: float, expected_result: str) -> None:
    assert _format_nsec_as_ns(nsec) == expected_result


@pytest.mark.parametrize(
    "nsec, expected_result",
    [
        (1e3 * 6.55003, "   6.55 µs"),
        (1e3 * 12.33002, "  12.33 µs"),
        (1e3 * 345.11001, " 345.11 µs"),
        (1e3 * 1999.7799, "1999.78 µs"),
    ],
)
def test_format_nsec_as_us(nsec: float, expected_result: str) -> None:
    assert _format_nsec_as_us(nsec) == expected_result


@pytest.mark.parametrize(
    "nsec, expected_result",
    [
        (1e6 * 6.55003, "   6.55 ms"),
        (1e6 * 12.33002, "  12.33 ms"),
        (1e6 * 345.11001, " 345.11 ms"),
        (1e6 * 1999.7799, "1999.78 ms"),
    ],
)
def test_format_nsec_as_ms(nsec: float, expected_result: str) -> None:
    assert _format_nsec_as_ms(nsec) == expected_result


@pytest.mark.parametrize(
    "nsec, expected_result",
    [
        (1e9 * 6.55003, "   6.55 s"),
        (1e9 * 12.33002, "  12.33 s"),
        (1e9 * 345.11001, " 345.11 s"),
        (1e9 * 1999.7799, "1999.78 s"),
    ],
)
def test_format_nsec_as_s(nsec: float, expected_result: str) -> None:
    assert _format_nsec_as_s(nsec) == expected_result


@pytest.mark.parametrize(
    "q25, q50, q75, expected_snippets_included, expected_snippets_excluded",
    [
        (100, 200, 400, ["±", "ns", "200.00", "150.00"], ["µs", "ms"]),
        (100, 200, 4100, ["±", "ns", "200.00", "2000.00"], ["µs", "ms"]),
        (190, 200, 210, ["±", "ns", "200.00", "10.00"], ["µs", "ms"]),
        (1e3 * 100, 1e3 * 200, 1e3 * 400, ["±", "µs", "200.00", "150.00"], ["ns", "ms"]),
        (1e3 * 100, 1e3 * 200, 1e3 * 4100, ["±", "µs", "200.00", "2000.00"], ["ns", "ms"]),
        (1e3 * 190, 1e3 * 200, 1e3 * 210, ["±", "µs", "200.00", "10.00"], ["ns", "ms"]),
        (1e6 * 100, 1e6 * 200, 1e6 * 400, ["±", "ms", "200.00", "150.00"], ["ns", "µs"]),
        (1e6 * 100, 1e6 * 200, 1e6 * 4100, ["±", "ms", "200.00", "2000.00"], ["ns", "µs"]),
        (1e6 * 190, 1e6 * 200, 1e6 * 210, ["±", "ms", "200.00", "10.00"], ["ns", "µs"]),
        (1e9 * 100, 1e9 * 200, 1e9 * 400, ["±", "s", "200.00", "150.00"], ["ns", "µs", "ms"]),
        (1e9 * 100, 1e9 * 200, 1e9 * 4100, ["±", "s", "200.00", "2000.00"], ["ns", "µs", "ms"]),
        (1e9 * 190, 1e9 * 200, 1e9 * 210, ["±", "s", "200.00", "10.00"], ["ns", "µs", "ms"]),
    ],
)
def test_format_time_durations(
    q25: float, q50: float, q75: float, expected_snippets_included: list[str], expected_snippets_excluded: list[str]
) -> None:
    # --- act ---------------------------------------------
    formatted = format_time_durations(q25, q50, q75)

    # --- assert ------------------------------------------
    assert all([s in formatted for s in expected_snippets_included])
    assert not any([s in formatted for s in expected_snippets_excluded])


# =================================================================================================
#  Timing
# =================================================================================================
def test_timer():
    # --- arrange -----------------------------------------
    timer = Timer()

    # --- assert 1 ----------------------------------------
    with pytest.raises(RuntimeError):
        t = timer.t_elapsed_sec()

    # --- act ---------------------------------------------
    with timer:
        time.sleep(0.1)

    # --- assert ------------------------------------------
    assert 0.05 < timer.t_elapsed_sec() < 0.15, "t_elapsed_sec() result incorrect."
    assert 50_000_000 < timer.t_elapsed_nsec() < 150_000_000, "t_elapsed_nsec() result incorrect."


def test_timer_running():
    # --- arrange -----------------------------------------
    timer = Timer()

    # --- act ---------------------------------------------
    with timer as t:
        t_before = timer.t_elapsed_sec()
        time.sleep(0.1)
        t_after = timer.t_elapsed_sec()

    # --- assert ------------------------------------------
    assert t_after >= t_before + 0.05, "t_elapsed_sec() did not increase while timer was running."
