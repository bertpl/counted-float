import psutil


def get_cpu_frequency_current() -> float:
    """Use psutil - with some fallbacks - to determine current CPU frequency in MHz."""
    try:
        return psutil.cpu_freq().current
    except AttributeError:
        return 1000.0  # fallback to 1000 MHz if psutil cannot provide the info


def get_cpu_frequency_min_max() -> tuple[float, float]:
    """Use psutil - with some fallbacks - to determine min, max CPU frequency in MHz."""
    try:
        return psutil.cpu_freq().min, psutil.cpu_freq().max
    except AttributeError:
        return 0.0, 1000.0  # fallback to (0 - 1000) MHz if psutil cannot provide the info
