def compute_per_op_latency(nsec: float, n_ops: int, cpu_freq_mhz: float) -> float:
    """Computes how many clock cycles 1 operation takes to execute give a value for nsec/ n ops & cpu freq in MHz."""
    nsec_per_clock_cycle = 1000 / cpu_freq_mhz
    return (nsec / n_ops) / nsec_per_clock_cycle


def per_op_latency_str(nsec_mean: float, nsec_std: float, n_ops: int, cpu_freq_mhz: float) -> str:
    latency_mean = compute_per_op_latency(nsec_mean, n_ops, cpu_freq_mhz)
    latency_std = compute_per_op_latency(nsec_std, n_ops, cpu_freq_mhz)
    return f"{latency_mean:5.2f} ± {latency_std:.2f}"
