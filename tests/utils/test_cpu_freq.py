from types import SimpleNamespace

import psutil
import pytest

from counted_float._core.utils import (
    get_cpu_frequency_mhz_current,
    get_cpu_frequency_mhz_max,
    get_cpu_frequency_mhz_min,
)
from counted_float._core.utils._cpu_freq import _get_psutil_cpu_freq_attribute_mhz


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


@pytest.mark.parametrize(("raw_reading", "expected_mhz"), [(3.5, 3500.0), (3.5e6, 3500.0)])
def test_cpu_freq_normalizes_out_of_range_readings(monkeypatch, raw_reading, expected_mhz):
    # a GHz-valued reading (far below ~63 MHz) is scaled up; a Hz-valued one (far above ~63 GHz)
    # is scaled down -- both land in the MHz range
    # --- arrange -----------------------------------------
    # raising=False: psutil.cpu_freq does not exist on every platform (e.g. macOS), so inject it
    monkeypatch.setattr(
        psutil,
        "cpu_freq",
        lambda: SimpleNamespace(min=raw_reading, max=raw_reading, current=raw_reading),
        raising=False,
    )

    # --- act ---------------------------------------------
    result = _get_psutil_cpu_freq_attribute_mhz("min")

    # --- assert ------------------------------------------
    assert result == expected_mhz
