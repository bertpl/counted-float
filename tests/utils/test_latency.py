import pytest

from counted_float._core.utils import convert_nsecs_to_cycles


@pytest.mark.parametrize(
    ("nsec", "cpu_freq_mhz", "fallback_freq_mhz", "expected_result"),
    [
        (1.0, 1000, 1000, 1.0),
        (2.0, 1000, 1000, 2.0),
        (2.0, 4000, 1000, 8.0),
        (3.0, None, 1000, 3.0),
        (3.0, None, 2000, 6.0),
        (5.0, 0, 3000, 15.0),
    ],
)
def test_convert_nsecs_to_cycles(nsec, cpu_freq_mhz: float | None, fallback_freq_mhz: float, expected_result: float):
    # --- act ---------------------------------------------
    result = convert_nsecs_to_cycles(
        nsec=nsec,
        cpu_freq_mhz=cpu_freq_mhz,
        fallback_freq_mhz=fallback_freq_mhz,
    )

    # --- assert ------------------------------------------
    assert result == pytest.approx(expected_result)


def test_convert_nsecs_to_cycles_uses_default_fallback_freq_mhz():
    # with cpu_freq_mhz None and no explicit fallback, the default fallback_freq_mhz=1000 must apply;
    # a mutated default (e.g. 2000) would double the result and fail this pin
    # --- act ---------------------------------------------
    result = convert_nsecs_to_cycles(nsec=3.0, cpu_freq_mhz=None)

    # --- assert ------------------------------------------
    assert result == pytest.approx(3.0)
