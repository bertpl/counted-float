"""Context manager that conveniently allows collection of flop counts for the enclosed code block.

Also provides .pause() and .resume() methods to control flop counting.
"""

import threading
from types import TracebackType
from typing import Self

from counted_float._core.counting._math_patching import apply_math_patches, remove_math_patches
from counted_float._core.counting._thread_counter import THREAD_COUNTER
from counted_float._core.models import FlopCounts

_CROSS_THREAD_MESSAGE = (
    "FlopCountingContext is confined to the thread that opened it; open a separate context per thread"
)


# =================================================================================================
#  FlopCountingContext
# =================================================================================================
class FlopCountingContext:
    """Context manager that can be used to count FLOP operations in a block of code.

    Only floating-point operations of CountedFloat objects are counted.  So make sure all math uses this type.

    Counting state is per-thread: this context measures only the thread that opened it, and is
    confined to that thread while active (cross-thread use raises RuntimeError; without the guard
    a cross-thread call would silently read or pause the *caller's* thread state).  To measure a
    multi-threaded computation, open a separate context per worker thread and sum the results.

    LIMITATIONS:
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
        #   - current count == THREAD_COUNTER - self.__cnt_start_snapshot
        self.__active: bool = False

        # Number of with-blocks currently open on this instance.  Only the outermost one drives
        # counting, so re-entering the same instance yields a single, unbroken count.
        self.__depth: int = 0

        # ident of the thread that opened the outermost with-block; None while no block is open.
        # Set at the 0->1 __enter__ and cleared at the 1->0 __exit__ only, so sequential reuse of
        # one instance across threads keeps working.
        self.__owner_ident: int | None = None

        # flop count bookkeeping
        self.__cnt_subtotal: FlopCounts = FlopCounts()
        self.__cnt_start_snapshot: FlopCounts = FlopCounts()

    # -------------------------------------------------------------------------
    #  Properties
    # -------------------------------------------------------------------------
    def is_active(self) -> bool:
        return self.__active

    def flop_counts(self) -> FlopCounts:
        """Returns current total flop count for this context manager.  See constructor comments for details.

        Raises:
            RuntimeError: If called from another thread while this context's with-block is open.
        """
        if self.__active:
            # while active, the count is derived from the owning thread's counter state, which is
            # meaningless (and misleading) when read from any other thread; while inactive (also
            # when paused), only the frozen subtotal is read, which is safe from any thread
            self.__require_owner_thread()
            return THREAD_COUNTER.flop_counts() - self.__cnt_start_snapshot
        return self.__cnt_subtotal.copy()

    # -------------------------------------------------------------------------
    #  Pause/Resume
    # -------------------------------------------------------------------------
    def pause(self) -> None:
        """Stop registering counts on this context until resume() is called.

        Raises:
            RuntimeError: If this context has no with-block open, or when called from another
                thread than the one that opened it.
        """
        self.__require_open("pause")
        self.__require_owner_thread()
        self.__deactivate()

    def resume(self) -> None:
        """Resume registering counts on this context after a pause().

        Raises:
            RuntimeError: If this context has no with-block open, or when called from another
                thread than the one that opened it.
        """
        self.__require_open("resume")
        self.__require_owner_thread()
        self.__activate()

    # -------------------------------------------------------------------------
    #  Internal state transitions
    # -------------------------------------------------------------------------
    def __require_open(self, action: str) -> None:
        """Reject a pause/resume attempted outside this context's with-block.

        Outside the block the math module is no longer patched, so registering counts there
        would silently blend instrumented operator semantics with un-instrumented `math.*`
        ones into a single count.

        Args:
            action: Name of the attempted operation, used in the error message.

        Raises:
            RuntimeError: If this context has no with-block open.
        """
        if self.__depth == 0:
            raise RuntimeError(f"cannot {action}() a FlopCountingContext outside its 'with' block")

    def __require_owner_thread(self) -> None:
        """Reject an operation attempted from another thread than the one that opened this context.

        Raises:
            RuntimeError: If the calling thread is not the owner thread.
        """
        if self.__owner_ident is not None and threading.get_ident() != self.__owner_ident:
            raise RuntimeError(_CROSS_THREAD_MESSAGE)

    def __activate(self) -> None:
        """Start attributing the thread's counts to this context, preserving any earlier subtotal."""
        if not self.__active:
            self.__cnt_start_snapshot = THREAD_COUNTER.flop_counts() - self.__cnt_subtotal
            self.__cnt_subtotal = FlopCounts()
            self.__active = True

    def __deactivate(self) -> None:
        """Freeze the running count into the subtotal and stop attributing the thread's counts."""
        if self.__active:
            self.__cnt_subtotal = self.flop_counts()
            self.__cnt_start_snapshot = FlopCounts()
            self.__active = False

    # -------------------------------------------------------------------------
    #  Context manager interface
    # -------------------------------------------------------------------------
    def __enter__(self) -> Self:
        if self.__depth == 0:
            self.__owner_ident = threading.get_ident()
        else:
            self.__require_owner_thread()  # re-entering an open context from another thread
        # patching the math module is tied to the with-block lifetime (not to pause()/resume(),
        # which only control whether counts are registered)
        apply_math_patches()
        self.__depth += 1
        if self.__depth == 1:
            self.__activate()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.__require_owner_thread()
        self.__depth -= 1
        if self.__depth == 0:
            self.__deactivate()
            self.__owner_ident = None
        remove_math_patches()


# =================================================================================================
#  PauseFlopCounting
# =================================================================================================
class PauseFlopCounting:
    """Context manager that pauses flop counting for the enclosed code block.

    This acts on the calling thread, across all of that thread's active FlopCountingContext
    instances.  On exit the counter's prior state is restored (rather than counting being resumed
    unconditionally), so these blocks can be nested and can sit inside code that already paused
    counting.

    Like FlopCountingContext, an instance is confined to the thread that entered it: exiting from
    another thread raises RuntimeError (it would silently resume the *caller's* thread counter).
    """

    def __init__(self) -> None:
        self.__was_active: bool = False
        self.__owner_ident: int | None = None

    def __enter__(self) -> Self:
        self.__owner_ident = threading.get_ident()
        self.__was_active = THREAD_COUNTER.is_active()
        THREAD_COUNTER.pause()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if threading.get_ident() != self.__owner_ident:
            raise RuntimeError(
                "PauseFlopCounting is confined to the thread that entered it; pause each thread separately"
            )
        self.__owner_ident = None
        if self.__was_active:
            THREAD_COUNTER.resume()
