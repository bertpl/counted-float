from types import SimpleNamespace

import pytest

from counted_float._core.benchmarking.flops.cpu_freq import (
    _get_psutil_cpu_freq_attribute_mhz,
    get_cpu_frequency_mhz_current,
    get_cpu_frequency_mhz_max,
    get_cpu_frequency_mhz_min,
)

psutil = pytest.importorskip("psutil", reason="these helpers read their frequencies through psutil")


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


@pytest.mark.parametrize("raw_reading", [None, 0.0, -1.0])
def test_cpu_freq_none_zero_or_negative_reading_returns_none(monkeypatch, raw_reading):
    # a None, zero, or negative reading must deterministically yield None (the `value <= 0.0` guard);
    # this pins all three cases so a `<=`→`<`, `or`→`and`, or dropped `is None` mutant is caught
    # --- arrange -----------------------------------------
    monkeypatch.setattr(
        psutil,
        "cpu_freq",
        lambda: SimpleNamespace(min=raw_reading, max=raw_reading, current=raw_reading),
        raising=False,
    )

    # --- act ---------------------------------------------
    result = _get_psutil_cpu_freq_attribute_mhz("min")

    # --- assert ------------------------------------------
    assert result is None


def test_cpu_freq_missing_attribute_returns_none(monkeypatch):
    # if psutil.cpu_freq() lacks the requested attribute, the AttributeError branch sets value=0.0 → None
    # --- arrange -----------------------------------------
    monkeypatch.setattr(psutil, "cpu_freq", SimpleNamespace, raising=False)  # called with no args -> empty namespace

    # --- act ---------------------------------------------
    result = _get_psutil_cpu_freq_attribute_mhz("current")

    # --- assert ------------------------------------------
    assert result is None


def test_cpu_freq_wrappers_read_distinct_attributes(monkeypatch):
    # each public wrapper must read its own attribute literal; distinct in-range values make a
    # swapped "min"/"current"/"max" literal break both the exact reads and min ≤ current ≤ max
    # --- arrange -----------------------------------------
    monkeypatch.setattr(
        psutil,
        "cpu_freq",
        lambda: SimpleNamespace(min=1000.0, current=2000.0, max=3000.0),
        raising=False,
    )

    # --- act ---------------------------------------------
    freq_min = get_cpu_frequency_mhz_min()
    freq_current = get_cpu_frequency_mhz_current()
    freq_max = get_cpu_frequency_mhz_max()

    # --- assert ------------------------------------------
    assert freq_min == 1000.0
    assert freq_current == 2000.0
    assert freq_max == 3000.0
    assert freq_min <= freq_current <= freq_max
