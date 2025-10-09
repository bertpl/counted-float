from counted_float._core.utils import (
    get_cpu_frequency_mhz_current,
    get_cpu_frequency_mhz_max,
    get_cpu_frequency_mhz_min,
)


def test_get_cpu_frequency_mhz_min_max_current():
    # --- act ---------------------------------------------
    freq_min = get_cpu_frequency_mhz_min()
    freq_max = get_cpu_frequency_mhz_max()
    freq_current = get_cpu_frequency_mhz_current()

    # --- assert ------------------------------------------
    assert freq_min is None or freq_min > 0.0
    assert freq_max is None or freq_max > 0.0
    assert freq_current is None or freq_current > 0.0

    if (freq_min is not None) and (freq_max is not None):
        assert freq_min <= freq_max
    if (freq_min is not None) and (freq_current is not None):
        assert freq_min <= freq_current
    if (freq_current is not None) and (freq_max is not None):
        assert freq_current <= freq_max
