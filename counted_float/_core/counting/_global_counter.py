from counted_float._core.models import FlopCounts


class GlobalFlopCounter:
    """
    Global counter for FLOP operations.  Essentially this class wraps around a FlopCounts object,
    limiting access to its fields (only allowing incrementing them) and providing a way to access copies of the counts.
    On top of this, the class allows pausing and resuming counting globally.
    """

    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self):
        self.__counts = FlopCounts()
        self.__incr = 1  # 1 if enabled, 0 if paused

    # -------------------------------------------------------------------------
    #  Pause / Resume / Status API
    # -------------------------------------------------------------------------
    def pause(self):
        self.__incr = 0

    def resume(self):
        self.__incr = 1

    def reset(self):
        self.__counts.reset()
        self.resume()

    def is_active(self) -> bool:
        return self.__incr > 0

    def flop_counts(self) -> FlopCounts:
        return self.__counts.copy()

    def total_count(self) -> int:
        """Shorthand for self.flop_counts().total_count()"""
        return self.__counts.total_count()

    def __getattr__(self, item):
        # provide shorthand access to the counts
        if item in FlopCounts.field_names():
            return getattr(self.__counts, item)
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    # -------------------------------------------------------------------------
    #  Incrementing counts
    # -------------------------------------------------------------------------
    def incr_abs(self):
        self.__counts.ABS += self.__incr

    def incr_minus(self):
        self.__counts.MINUS += self.__incr

    def incr_comp(self):
        self.__counts.COMP += self.__incr

    def incr_rnd(self):
        self.__counts.RND += self.__incr

    def incr_f2i(self):
        self.__counts.F2I += self.__incr

    def incr_i2f(self):
        self.__counts.I2F += self.__incr

    def incr_add(self):
        self.__counts.ADD += self.__incr

    def incr_sub(self):
        self.__counts.SUB += self.__incr

    def incr_mul(self):
        self.__counts.MUL += self.__incr

    def incr_div(self):
        self.__counts.DIV += self.__incr

    def incr_sqrt(self):
        self.__counts.SQRT += self.__incr

    def incr_cbrt(self):
        self.__counts.CBRT += self.__incr

    def incr_exp(self):
        self.__counts.EXP += self.__incr

    def incr_exp2(self):
        self.__counts.EXP2 += self.__incr

    def incr_exp10(self):
        self.__counts.EXP10 += self.__incr

    def incr_log(self):
        self.__counts.LOG += self.__incr

    def incr_log2(self):
        self.__counts.LOG2 += self.__incr

    def incr_log10(self):
        self.__counts.LOG10 += self.__incr

    def incr_pow(self):
        self.__counts.POW += self.__incr

    def incr_sin(self):
        self.__counts.SIN += self.__incr

    def incr_cos(self):
        self.__counts.COS += self.__incr

    def incr_tan(self):
        self.__counts.TAN += self.__incr


# --- global variable through which we access the global counter ---
GLOBAL_COUNTER = GlobalFlopCounter()
