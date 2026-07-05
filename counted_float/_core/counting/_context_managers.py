"""
Context manager that conveniently allows collection of flop counts for the enclosed code block,
as well as providing .pause() and .resume() methods to control flop counting.
"""

from counted_float._core.counting._global_counter import GLOBAL_COUNTER
from counted_float._core.counting._math_patching import apply_math_patches, remove_math_patches
from counted_float._core.models import FlopCounts


# =================================================================================================
#  FlopCountingContext
# =================================================================================================
class FlopCountingContext:
    """
    Context manager that can be used to count FLOP operations in a block of code.  Only floating-point
    operations of CountedFloat objects are counted.  So make sure all math uses this type.

    LIMITATIONS:
        - this context manager is not thread-safe
        - not _all_ floating-point operations are counted, see the docs for more details.
    """

    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self):
        # Active/inactive flag  (toggled by __enter__ and __exit__ + by pause() and resume() methods)
        # When inactive:
        #   - current count == self.__cnt_subtotal
        # When active:
        #   - current count == GLOBAL_COUNTER - self.__cnt_start_snapshot
        self.__active: bool = False

        # flop count bookkeeping
        self.__cnt_subtotal: FlopCounts = FlopCounts()
        self.__cnt_start_snapshot: FlopCounts = FlopCounts()

    # -------------------------------------------------------------------------
    #  Properties
    # -------------------------------------------------------------------------
    def is_active(self) -> bool:
        return self.__active

    def flop_counts(self) -> FlopCounts:
        """Returns current total flop count for this context manager.  See constructor comments for details."""
        if self.__active:
            return GLOBAL_COUNTER.flop_counts() - self.__cnt_start_snapshot
        return self.__cnt_subtotal.copy()

    # -------------------------------------------------------------------------
    #  Pause/Resume
    # -------------------------------------------------------------------------
    def pause(self):
        if self.__active:
            self.__cnt_subtotal = self.flop_counts()
            self.__cnt_start_snapshot = FlopCounts()
            self.__active = False

    def resume(self):
        if not self.__active:
            self.__cnt_start_snapshot = GLOBAL_COUNTER.flop_counts() - self.__cnt_subtotal
            self.__cnt_subtotal = FlopCounts()
            self.__active = True

    # -------------------------------------------------------------------------
    #  Context manager interface
    # -------------------------------------------------------------------------
    def __enter__(self):
        # patching the math module is tied to the with-block lifetime (not to pause()/resume(),
        # which only control whether counts are registered)
        apply_math_patches()
        self.resume()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pause()
        remove_math_patches()


# =================================================================================================
#  PauseFlopCounting
# =================================================================================================
class PauseFlopCounting:
    """
    Context manager that pauses flop counting for the enclosed code block.  This acts globally, across all
    active FlopCountingContext instances.
    """

    def __enter__(self):
        GLOBAL_COUNTER.pause()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        GLOBAL_COUNTER.resume()
