def convert_nsecs_to_cycles(nsec: float, cpu_freq_mhz: float | None, fallback_freq_mhz: float = 1000) -> float:
    """Computes how many clock cycles the provide time duration (nsec) lasts, given the cpu freq in MHz"""
    return (1e-3 * (cpu_freq_mhz or fallback_freq_mhz)) * nsec
