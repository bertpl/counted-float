import pytest

from counted_float._core.utils._formatting import (
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
    "nsec, expected_result",
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
    ],
)
def test_format_time_duration(nsec: float, expected_result: str) -> None:
    assert format_time_duration(nsec) == expected_result


# =================================================================================================
#  Format latencies
# =================================================================================================
@pytest.mark.parametrize(
    "n_cycles, expected_result",
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
    ],
)
def test_format_latency(n_cycles: float, expected_result: str):
    assert format_latency(n_cycles) == expected_result
