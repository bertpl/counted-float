import math

import psutil


# =================================================================================================
#  Get Min, Max, Current CPU frequency in MHz
# =================================================================================================
def get_cpu_frequency_mhz_min() -> float:
    """Use psutil - with some fallbacks - to determine MIN CPU frequency in MHz."""
    return _get_psutil_cpu_freq_attribute_mhz("min", fallback=1000.0)


def get_cpu_frequency_mhz_max() -> float:
    """Use psutil - with some fallbacks - to determine MAX CPU frequency in MHz."""
    return _get_psutil_cpu_freq_attribute_mhz("max", fallback=1000.0)


def get_cpu_frequency_mhz_current() -> float:
    """Use psutil - with some fallbacks - to determine CURRENT CPU frequency in MHz."""
    return _get_psutil_cpu_freq_attribute_mhz("current", fallback=1000.0)


# =================================================================================================
#  Internal helper
# =================================================================================================
def _get_psutil_cpu_freq_attribute_mhz(att_name: str, fallback: float) -> float:
    """Helper to get an attribute from psutil.cpu_freq(), with a fallback value & heuristics to distinguish Mhz & GHz"""
    try:
        value = getattr(psutil.cpu_freq(), att_name)
    except AttributeError:
        value = 0.0

    if (value is None) or (value <= 0.0):
        return fallback
    else:
        valid_range_min_mhz = 2000 / math.sqrt(1000)  # ~ 63 MHz
        valid_range_max_mhz = 2000 * math.sqrt(1000)  # ~ 63 GHz
        while value < valid_range_min_mhz:
            value *= 1000.0
        while value > valid_range_max_mhz:
            value /= 1000.0
        return value
