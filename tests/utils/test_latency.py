import pytest

from counted_float._core.utils import convert_nsecs_to_cycles


@pytest.mark.parametrize(
    "nsec, cpu_freq_mhz, expected_result",
    [
        (1.0, 1000, 1.0),
        (2.0, 1000, 2.0),
        (2.0, 4000, 8.0),
    ],
)
def test_convert_nsecs_to_cycles(nsec, cpu_freq_mhz: float, expected_result: float):
    # --- act & assert ------------------------------------
    assert convert_nsecs_to_cycles(nsec=nsec, cpu_freq_mhz=cpu_freq_mhz) == pytest.approx(expected_result)
