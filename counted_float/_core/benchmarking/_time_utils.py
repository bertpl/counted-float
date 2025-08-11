import time


# =================================================================================================
#  Formatting
# =================================================================================================
def format_time_durations(nsec_q25: float, nsec_q50: float, nsec_q75: float) -> str:
    if nsec_q50 < 1e3:
        formatter = _format_nsec_as_ns
    elif nsec_q50 < 1e6:
        formatter = _format_nsec_as_us
    elif nsec_q50 < 1e9:
        formatter = _format_nsec_as_ms
    else:
        formatter = _format_nsec_as_s

    return f"{formatter(nsec_q50)} ± {formatter((nsec_q75 - nsec_q25) / 2)} / operation"


def _format_nsec_as_ns(nsec: float) -> str:
    return f"{nsec:7.2f} ns"


def _format_nsec_as_us(nsec: float) -> str:
    return f"{nsec / 1e3:7.2f} µs"


def _format_nsec_as_ms(nsec: float) -> str:
    return f"{nsec / 1e6:7.2f} ms"


def _format_nsec_as_s(nsec: float) -> str:
    return f"{nsec / 1e9:7.2f} s"


# =================================================================================================
#  Timing
# =================================================================================================
class Timer:
    """
    Class acting as a context manager to measure time elapsed.  Elapsed time can be retrieved using t_elapsed().
    """

    # --- constructor -------------------------------------
    def __init__(self):
        self._start: float | None = None
        self._end: float | None = None

    # --- context manager ---------------------------------
    def __enter__(self):
        self._start = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end = time.perf_counter_ns()

    # --- extract results ---------------------------------
    def t_elapsed_nsec(self) -> float:
        if self._start is None:
            raise RuntimeError("Timer has not been started.")

        if self._end is None:
            # timer still running
            return time.perf_counter_ns() - self._start
        else:
            # timer finished
            return self._end - self._start

    def t_elapsed_sec(self) -> float:
        return self.t_elapsed_nsec() / 1e9
