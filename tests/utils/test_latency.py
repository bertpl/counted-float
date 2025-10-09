import pytest

from counted_float._core.utils import convert_nsecs_to_cycles


@pytest.mark.parametrize(
    "nsec, cpu_freq_mhz, fallback_freq_mhz, expected_result",
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
