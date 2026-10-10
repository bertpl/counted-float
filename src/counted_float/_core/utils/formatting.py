# =================================================================================================
#  Time durations
# =================================================================================================
def format_time_duration(nsec: float) -> str:
    if nsec < 1e3:
        return _format_nsec_as_ns(nsec)
    elif nsec < 1e6:
        return _format_nsec_as_us(nsec)
    elif nsec < 1e9:
        return _format_nsec_as_ms(nsec)
    else:
        return _format_nsec_as_s(nsec) + " "  # add trailing whitespace to right-align well with other cases


def _format_nsec_as_ns(nsec: float) -> str:
    return f"{nsec:7.2f} ns"


def _format_nsec_as_us(nsec: float) -> str:
    return f"{nsec / 1e3:7.2f} µs"


def _format_nsec_as_ms(nsec: float) -> str:
    return f"{nsec / 1e6:7.2f} ms"


def _format_nsec_as_s(nsec: float) -> str:
    return f"{nsec / 1e9:7.2f} s"


# =================================================================================================
#  Format latencies
# =================================================================================================
def format_latency(n_cycles: float) -> str:
    if round(n_cycles, 2) < 10:
        return f" {n_cycles:4.2f} cpu cycles"
    elif round(n_cycles, 1) < 100:
        return f" {n_cycles:4.1f} cpu cycles"
    elif round(n_cycles, 0) < 1_000:
        return f" {n_cycles:4.0f} cpu cycles"
    elif round(n_cycles, -1) < 10_000:
        return f"{n_cycles / 1e3:4.2f}K cpu cycles"
    elif round(n_cycles, -2) < 100_000:
        return f"{n_cycles / 1e3:4.1f}K cpu cycles"
    elif round(n_cycles, -3) < 1_000_000:
        return f"{n_cycles / 1e3:4.0f}K cpu cycles"
    else:
        return f"{n_cycles / 1e6:4.2f}M cpu cycles"
