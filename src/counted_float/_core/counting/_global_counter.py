from counted_float._core.models import FlopCounts


class GlobalFlopCounter:
    """Global counter for FLOP operations.

    Essentially this class wraps around a FlopCounts object, limiting access to its fields (only allowing
    incrementing them) and providing a way to access copies of the counts.
    On top of this, the class allows pausing and resuming counting globally.
    """

    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        self.__counts = FlopCounts()
        self.__incr = 1  # 1 if enabled, 0 if paused

    # -------------------------------------------------------------------------
    #  Pause / Resume / Status API
    # -------------------------------------------------------------------------
    def pause(self) -> None:
        self.__incr = 0

    def resume(self) -> None:
        self.__incr = 1

    def reset(self) -> None:
        self.__counts.reset()
        self.resume()

    def is_active(self) -> bool:
        return self.__incr > 0

    def flop_counts(self) -> FlopCounts:
        return self.__counts.copy()

    def total_count(self) -> int:
        """Shorthand for self.flop_counts().total_count()."""
        return self.__counts.total_count()

    def __getattr__(self, item: str) -> int:
        # provide shorthand access to the counts
        if item in FlopCounts.field_names():
            return getattr(self.__counts, item)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    # -------------------------------------------------------------------------
    #  Incrementing counts
    # -------------------------------------------------------------------------
    def incr_abs(self) -> None:
        self.__counts.ABS += self.__incr

    def incr_minus(self) -> None:
        self.__counts.MINUS += self.__incr

    def incr_comp(self) -> None:
        self.__counts.COMP += self.__incr

    def incr_rnd(self) -> None:
        self.__counts.RND += self.__incr

    def incr_f2i(self) -> None:
        self.__counts.F2I += self.__incr

    def incr_i2f(self) -> None:
        self.__counts.I2F += self.__incr

    def incr_add(self) -> None:
        self.__counts.ADD += self.__incr

    def incr_sub(self) -> None:
        self.__counts.SUB += self.__incr

    def incr_mul(self) -> None:
        self.__counts.MUL += self.__incr

    def incr_div(self) -> None:
        self.__counts.DIV += self.__incr

    def incr_sqrt(self) -> None:
        self.__counts.SQRT += self.__incr

    def incr_cbrt(self) -> None:
        self.__counts.CBRT += self.__incr

    def incr_exp(self) -> None:
        self.__counts.EXP += self.__incr

    def incr_exp2(self) -> None:
        self.__counts.EXP2 += self.__incr

    def incr_exp10(self) -> None:
        self.__counts.EXP10 += self.__incr

    def incr_log(self) -> None:
        self.__counts.LOG += self.__incr

    def incr_log2(self) -> None:
        self.__counts.LOG2 += self.__incr

    def incr_log10(self) -> None:
        self.__counts.LOG10 += self.__incr

    def incr_pow(self) -> None:
        self.__counts.POW += self.__incr

    def incr_sin(self) -> None:
        self.__counts.SIN += self.__incr

    def incr_cos(self) -> None:
        self.__counts.COS += self.__incr

    def incr_tan(self) -> None:
        self.__counts.TAN += self.__incr

    def incr_asin(self) -> None:
        self.__counts.ASIN += self.__incr

    def incr_acos(self) -> None:
        self.__counts.ACOS += self.__incr

    def incr_atan(self) -> None:
        self.__counts.ATAN += self.__incr

    def incr_atan2(self) -> None:
        self.__counts.ATAN2 += self.__incr

    def incr_hypot(self) -> None:
        self.__counts.HYPOT += self.__incr

    def incr_expm1(self) -> None:
        self.__counts.EXPM1 += self.__incr

    def incr_log1p(self) -> None:
        self.__counts.LOG1P += self.__incr

    def incr_fmod(self) -> None:
        self.__counts.FMOD += self.__incr


# --- global variable through which we access the global counter ---
GLOBAL_COUNTER = GlobalFlopCounter()
