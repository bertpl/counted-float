"""Context manager that conveniently allows collection of flop counts for the enclosed code block.

Also provides .pause() and .resume() methods to control flop counting.
"""

import threading
from types import TracebackType
from typing import Self

from counted_float._core.counting._math_patching import (
    apply_math_patches,
    apply_uncounted_math_patches,
    remove_math_patches,
    remove_uncounted_math_patches,
)
from counted_float._core.counting._thread_counter import THREAD_COUNTER
from counted_float._core.counting.verbosity import Verbosity
from counted_float._core.models import FlopCounts

_CROSS_THREAD_MESSAGE = (
    "FlopCountingContext is confined to the thread that opened it; open a separate context per thread"
)
_PAUSE_CROSS_THREAD_MESSAGE = (
    "PauseFlopCounting is confined to the thread that entered it; pause each thread separately"
)
_PAUSE_REENTRY_MESSAGE = "PauseFlopCounting is already active; use a separate instance per 'with' block"


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

    Pass a `verbosity` level to have the context report each flop as it is registered, instead of
    only totalling them (see Verbosity).

    LIMITATIONS:
        - not _all_ floating-point operations are counted, see the docs for more details.
    """

    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self, verbosity: Verbosity = Verbosity.OFF) -> None:
        """Create a counting context.

        Args:
            verbosity: What to report about the flops registered while this context's with-block
                is open.  The level applies to the whole thread, so a context opened inside this
                one takes over until it exits, whatever level it asks for.
        """
        # Verbosity requested by this context, and the thread level it replaced while open
        self.__verbosity: Verbosity = verbosity
        self.__replaced_verbosity: Verbosity = Verbosity.OFF

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

    def __enter_reporting_state(self) -> None:
        """Switch the thread to this context's verbosity level, and start reporting if it was not.

        The replacements that surface uncountable `math.*` calls exist only while some thread is
        reporting, so a context that takes its thread from silent to reporting is what installs
        them.
        """
        self.__replaced_verbosity = THREAD_COUNTER.set_verbosity(self.__verbosity)
        if self.__starts_reporting():
            apply_uncounted_math_patches()

    def __leave_reporting_state(self) -> None:
        """Restore the level this context replaced, and stop reporting if it started."""
        if self.__starts_reporting():
            remove_uncounted_math_patches()
        THREAD_COUNTER.set_verbosity(self.__replaced_verbosity)

    def __starts_reporting(self) -> bool:
        """Whether this context is the one taking its thread from silent to reporting.

        The same question answered in reverse on the way out, which is why entering and leaving
        share it: the pair of levels involved is the same either way.
        """
        return self.__replaced_verbosity is Verbosity.OFF and self.__verbosity is not Verbosity.OFF

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
            # only the outermost entry switches the level, and only the matching exit restores it:
            # re-entering this same context would otherwise overwrite the replaced level with its
            # own, leaving the final exit to restore that instead of the level from before the block
            self.__enter_reporting_state()
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
            self.__leave_reporting_state()
            self.__owner_ident = None
        remove_math_patches()


# =================================================================================================
#  PauseFlopCounting
# =================================================================================================
class PauseFlopCounting:
    """Context manager that pauses flop counting for the enclosed code block.

    This acts on the calling thread, across all of that thread's active FlopCountingContext
    instances.  On exit the counter's prior state is restored (rather than counting being resumed
    unconditionally), so a block can sit inside code that already paused counting, and blocks of
    separate instances nest.

    One instance covers one open block: entering an instance whose block is still open raises
    RuntimeError, since the state to restore has a single slot.  Construct the manager where the
    block is rather than holding one to reuse, and nesting takes care of itself.  (FlopCountingContext
    does re-enter on one instance, because it accumulates counts that are read off it afterwards -
    an identity worth keeping while open, which a pause has no equivalent of.)  Reusing an instance
    for a later, non-overlapping block is fine.

    Like FlopCountingContext, an instance is confined to the thread that entered it: exiting from
    another thread raises RuntimeError (it would silently resume the *caller's* thread counter).
    """

    def __init__(self) -> None:
        # State of the thread counter from before this block paused it, restored on exit
        self.__was_active: bool = False

        # ident of the thread that entered the block; None while no block is open, which is what
        # also makes it the liveness flag that the re-entry guard reads
        self.__owner_ident: int | None = None

    def __enter__(self) -> Self:
        if self.__owner_ident is not None:
            # refused before anything is written, so the open block keeps the state it saved:
            # catching this error still leaves its exit able to restore counting correctly
            raise RuntimeError(_PAUSE_REENTRY_MESSAGE)
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
            raise RuntimeError(_PAUSE_CROSS_THREAD_MESSAGE)
        self.__owner_ident = None
        if self.__was_active:
            THREAD_COUNTER.resume()
