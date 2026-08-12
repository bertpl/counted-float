import pytest

from counted_float._core.utils.formatting import (
    _format_nsec_as_ms,
    _format_nsec_as_ns,
    _format_nsec_as_s,
    _format_nsec_as_us,
    format_latency,
    format_time_duration,
)


# =================================================================================================
#  Time durations
# =================================================================================================
@pytest.mark.parametrize(
    ("nsec", "expected_result"),
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
    ("nsec", "expected_result"),
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
    ("nsec", "expected_result"),
    [
        (1e6 * 6.55003, "   6.55 ms"),
        (1e6 * 12.33002, "  12.33 ms"),
        (1e6 * 345.11001, " 345.11 ms"),
        (1e6 * 1999.7799, "1999.78 ms"),
        # just above the x.xx5 rounding boundary: only an exact 1e6 divisor still rounds up
        (2_005_001, "   2.01 ms"),
    ],
)
def test_format_nsec_as_ms(nsec: float, expected_result: str) -> None:
    assert _format_nsec_as_ms(nsec) == expected_result


@pytest.mark.parametrize(
    ("nsec", "expected_result"),
    [
        (1e9 * 6.55003, "   6.55 s"),
        (1e9 * 12.33002, "  12.33 s"),
        (1e9 * 345.11001, " 345.11 s"),
        (1e9 * 1999.7799, "1999.78 s"),
        # just above the x.xx5 rounding boundary: only an exact 1e9 divisor still rounds up
        (2_005_000_001, "   2.01 s"),
    ],
)
def test_format_nsec_as_s(nsec: float, expected_result: str) -> None:
    assert _format_nsec_as_s(nsec) == expected_result


@pytest.mark.parametrize(
    ("nsec", "expected_result"),
    [
        (0.0010000000000, "   0.00 ns"),
        (0.0100000000000, "   0.01 ns"),
        (6.5500300000000, "   6.55 ns"),
        (12.330020000000, "  12.33 ns"),
        (345.11001000000, " 345.11 ns"),
        (1e3 * 6.5500300, "   6.55 µs"),
        (1e3 * 12.330020, "  12.33 µs"),
        (1e3 * 345.11001, " 345.11 µs"),
        (1e6 * 6.5500300, "   6.55 ms"),
        (1e6 * 12.330020, "  12.33 ms"),
        (1e6 * 345.11001, " 345.11 ms"),
        (1e9 * 6.5500300, "   6.55 s "),
        (1e9 * 12.330020, "  12.33 s "),
        (1e9 * 345.11001, " 345.11 s "),
        (1e9 * 1999.7799, "1999.78 s "),
        # each unit boundary belongs to the larger unit
        (1e3, "   1.00 µs"),
        (1e6, "   1.00 ms"),
        (1e9, "   1.00 s "),
    ],
)
def test_format_time_duration(nsec: float, expected_result: str) -> None:
    assert format_time_duration(nsec) == expected_result


# =================================================================================================
#  Format latencies
# =================================================================================================
@pytest.mark.parametrize(
    ("n_cycles", "expected_result"),
    [
        (0.0012300000000, " 0.00 cpu cycles"),
        (0.0123000000000, " 0.01 cpu cycles"),
        (0.1230000000000, " 0.12 cpu cycles"),
        (1.2300000000000, " 1.23 cpu cycles"),
        (12.300000000000, " 12.3 cpu cycles"),
        (123.00000000000, "  123 cpu cycles"),
        (1230.0000000000, "1.23K cpu cycles"),
        (12300.000000000, "12.3K cpu cycles"),
        (123000.00000000, " 123K cpu cycles"),
        (1230000.0000000, "1.23M cpu cycles"),
        (9999.9999999999, "10.0K cpu cycles"),
        # each threshold, from the last value that still belongs to a branch to the first that does not
        (9.99, " 9.99 cpu cycles"),  # round(_, 2) < 10
        (10.0, " 10.0 cpu cycles"),  # round(_, 2) >= 10
        (99.9, " 99.9 cpu cycles"),  # round(_, 1) < 100
        (100.0, "  100 cpu cycles"),  # round(_, 1) >= 100
        (999.0, "  999 cpu cycles"),  # round(_, 0) < 1_000
        (1_000.0, "1.00K cpu cycles"),  # round(_, 0) >= 1_000
        (9_990.0, "9.99K cpu cycles"),  # round(_, -1) < 10_000
        (9_999.0, "10.0K cpu cycles"),  # round(_, -1) >= 10_000 -- the rounding crosses it, not the value
        (10_000.0, "10.0K cpu cycles"),  # round(_, -1) >= 10_000
        (99_900.0, "99.9K cpu cycles"),  # round(_, -2) < 100_000
        (100_000.0, " 100K cpu cycles"),  # round(_, -2) >= 100_000
        (999_000.0, " 999K cpu cycles"),  # round(_, -3) < 1_000_000
        (1_000_000.0, "1.00M cpu cycles"),  # round(_, -3) >= 1_000_000
        # values the threshold rounding carries across a branch boundary: each one pins the exact
        # precision of its branch's check, which the exact-boundary cases above cannot distinguish
        (9.996, " 10.0 cpu cycles"),  # round(_, 2) crosses 10; round(_, 3) would not
        (99.96, "  100 cpu cycles"),  # round(_, 1) crosses 100; round(_, 2) would not
        (999.6, "1.00K cpu cycles"),  # round(_, 0) crosses 1_000; round(_, 1) would not
        (99_960.0, " 100K cpu cycles"),  # round(_, -2) crosses 100_000; round to fewer digits would not
        (999_600.0, "1.00M cpu cycles"),  # round(_, -3) crosses 1_000_000; round to fewer digits would not
        (2_005_001.0, "2.01M cpu cycles"),  # just above the x.xx5 boundary: needs the exact 1e6 divisor
    ],
)
def test_format_latency(n_cycles: float, expected_result: str):
    assert format_latency(n_cycles) == expected_result
