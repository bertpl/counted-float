# used when a machine's real clock rate cannot be read; callers that rely on it warn, since the
# resulting "cycles" are nanoseconds under another name -- only scale-invariant ratios survive it
FALLBACK_CPU_FREQ_MHZ = 1000


def convert_nsecs_to_cycles(
    nsec: float, cpu_freq_mhz: float | None, fallback_freq_mhz: float = FALLBACK_CPU_FREQ_MHZ
) -> float:
    """Computes how many clock cycles the provide time duration (nsec) lasts, given the cpu freq in MHz."""
    return (1e-3 * (cpu_freq_mhz or fallback_freq_mhz)) * nsec
