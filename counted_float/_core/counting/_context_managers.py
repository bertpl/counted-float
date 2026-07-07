"""Context manager that conveniently allows collection of flop counts for the enclosed code block.

Also provides .pause() and .resume() methods to control flop counting.
"""

from types import TracebackType
from typing import Self

from counted_float._core.counting._global_counter import GLOBAL_COUNTER
from counted_float._core.counting._math_patching import apply_math_patches, remove_math_patches
from counted_float._core.models import FlopCounts


# =================================================================================================
#  FlopCountingContext
# =================================================================================================
class FlopCountingContext:
    """Context manager that can be used to count FLOP operations in a block of code.

    Only floating-point operations of CountedFloat objects are counted.  So make sure all math uses this type.

    LIMITATIONS:
        - this context manager is not thread-safe
        - not _all_ floating-point operations are counted, see the docs for more details.
    """

    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self) -> None:
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
    def pause(self) -> None:
        if self.__active:
            self.__cnt_subtotal = self.flop_counts()
            self.__cnt_start_snapshot = FlopCounts()
            self.__active = False

    def resume(self) -> None:
        if not self.__active:
            self.__cnt_start_snapshot = GLOBAL_COUNTER.flop_counts() - self.__cnt_subtotal
            self.__cnt_subtotal = FlopCounts()
            self.__active = True

    # -------------------------------------------------------------------------
    #  Context manager interface
    # -------------------------------------------------------------------------
    def __enter__(self) -> Self:
        # patching the math module is tied to the with-block lifetime (not to pause()/resume(),
        # which only control whether counts are registered)
        apply_math_patches()
        self.resume()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.pause()
        remove_math_patches()


# =================================================================================================
#  PauseFlopCounting
# =================================================================================================
class PauseFlopCounting:
    """Context manager that pauses flop counting for the enclosed code block.

    This acts globally, across all active FlopCountingContext instances.  On exit the counter's
    prior state is restored (rather than counting being resumed unconditionally), so these blocks
    can be nested and can sit inside code that already paused counting.
    """

    def __init__(self) -> None:
        self.__was_active: bool = False

    def __enter__(self) -> Self:
        self.__was_active = GLOBAL_COUNTER.is_active()
        GLOBAL_COUNTER.pause()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__was_active:
            GLOBAL_COUNTER.resume()
