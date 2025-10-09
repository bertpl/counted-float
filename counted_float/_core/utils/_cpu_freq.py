import math

import psutil


# =================================================================================================
#  Get Min, Max, Current CPU frequency in MHz
# =================================================================================================
def get_cpu_frequency_mhz_min() -> float | None:
    """Use psutil - with some fallbacks - to determine MIN CPU frequency in MHz."""
    return _get_psutil_cpu_freq_attribute_mhz("min")


def get_cpu_frequency_mhz_max() -> float | None:
    """Use psutil - with some fallbacks - to determine MAX CPU frequency in MHz."""
    return _get_psutil_cpu_freq_attribute_mhz("max")


def get_cpu_frequency_mhz_current() -> float | None:
    """Use psutil - with some fallbacks - to determine CURRENT CPU frequency in MHz."""
    return _get_psutil_cpu_freq_attribute_mhz("current")


# =================================================================================================
#  Internal helper
# =================================================================================================
def _get_psutil_cpu_freq_attribute_mhz(att_name: str) -> float | None:
    """
    Helper to get an attribute from psutil.cpu_freq(), returning None for missing or 0 data
    & heuristics to distinguish Mhz & GHz
    """
    try:
        value = getattr(psutil.cpu_freq(), att_name)
    except AttributeError:
        value = 0.0

    if (value is None) or (value <= 0.0):
        return None
    else:
        valid_range_min_mhz = 2000 / math.sqrt(1000)  # ~ 63 MHz
        valid_range_max_mhz = 2000 * math.sqrt(1000)  # ~ 63 GHz
        while value < valid_range_min_mhz:
            value *= 1000.0
        while value > valid_range_max_mhz:
            value /= 1000.0
        return value
