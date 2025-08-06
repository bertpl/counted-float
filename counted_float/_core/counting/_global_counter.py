from counted_float._core.counting.models import FlopCounts


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

    def incr_equals(self):
        self.__counts.EQUALS += self.__incr

    def incr_gte(self):
        self.__counts.GTE += self.__incr

    def incr_lte(self):
        self.__counts.LTE += self.__incr

    def incr_cmp_zero(self):
        self.__counts.CMP_ZERO += self.__incr

    def incr_rnd(self):
        self.__counts.RND += self.__incr

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

    def incr_pow2(self):
        self.__counts.POW2 += self.__incr

    def incr_log2(self):
        self.__counts.LOG2 += self.__incr

    def incr_pow(self):
        self.__counts.POW += self.__incr


# --- global variable through which we access the global counter ---
GLOBAL_COUNTER = GlobalFlopCounter()
