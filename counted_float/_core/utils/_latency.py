def compute_latency(nsec: float, cpu_freq_mhz: float) -> float:
    """Computes how many clock cycles the provide time duration (nsec) lasts, given the cpu freq in MHz"""
    return (1e-3 * cpu_freq_mhz) * nsec
