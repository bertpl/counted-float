"""Thread-local flop-counting state.

Each OS thread owns two FlopCounts objects, created lazily on the thread's first counter
access:

  - ``flop_counts_active``   : the thread's real counts (what counting contexts snapshot
                                and diff)
  - ``flop_counts_inactive`` : a sink that absorbs increments while counting is paused

``flop_counts`` is an alias pointing at one of the two, and increments always go through
the alias.  Because the alias always points at a valid counts object, an increment is
one unconditional statement — ``_TLS.flop_counts.<FIELD> += 1`` — whether counting is
paused or not; pause() and resume() just repoint the alias.

A verbose thread points the alias at a third kind of target: a stand-in that logs each
increment on its way into ``flop_counts_active`` (see the verbosity subpackage).  It is
selected by the same repointing, so verbose counting costs the counting sites nothing —
at level OFF the alias points at the plain counts, exactly as it would without the
feature.  Only the level itself (``verbosity``) is kept per thread; the stand-in is built
when a target is chosen, which happens only when one changes.

Two invariants follow from the alias having three possible targets, and both are pinned by
tests:

  - "is counting paused?" is ``flop_counts is flop_counts_inactive`` — never a comparison
    against ``flop_counts_active``, which a logging thread does not point at;
  - reading counts back goes to ``flop_counts_active`` directly, never through the alias,
    whose target is only ever a counts-shaped object to write through.

Two kinds of code interact with this state:

  - the **hot path**: the per-flop increments inside CountedFloat's operators and the
    patched ``math.*`` replacements — executed on every counted flop, so every nanosecond
    counts;
  - the **cold path**: occasional control operations — pause/resume/reset and reading
    counts — executed a handful of times per program, where clarity wins over speed.

Cold-path code goes through the ThreadLocalFlopCounter facade below: each method calls
``_ensure()`` (get-or-create the thread's state) and then operates with plain statements.
Hot-path code must NOT call facade methods — a Python method call costs about as much as
the increment itself — and instead inlines the increment together with its own lazy-init
handler:

    try:
        _TLS.flop_counts.ADD += 1
    except AttributeError:  # first counted op on this thread
        _create_thread_state().ADD += 1

The ``try`` costs nothing when no exception is raised, and the handler fires at most once
per thread: only the very first counter access on a thread finds ``_TLS`` empty.  The
handler performs the increment itself (on the object ``_create_thread_state`` returns),
so the operation that triggered initialization is still counted.

Why ``threading.local`` and not ``contextvars``: ContextVar lookups measured slightly
faster, but their semantics don't fit.  New threads start with an empty context, and
asyncio runs callbacks and tasks in *copies* of a context, so state initialized lazily
inside a task can fail to propagate outward — whether an enclosing FlopCountingContext
sees a task's counts would then depend on task-creation order.  Contexts also propagate
*into* worker threads (``asyncio.to_thread``, executor submissions), which would share
one mutable counts object across OS threads — the very data race this module exists to
remove.  ``threading.local`` has exactly one, unambiguous semantic: one independent state
per OS thread.
"""

from __future__ import annotations

import threading

from counted_float._core.models import FlopCounts

from .verbosity import LoggingFlopCounts, Verbosity

# What the ``flop_counts`` alias may point at: the thread's plain counts (active or the paused
# sink), or the logging stand-in a verbose thread writes through.  Counting sites treat the
# target as an opaque counts-shaped object, so which one is installed never reaches them.
CountsTarget = FlopCounts | LoggingFlopCounts

# A bare threading.local() rather than a subclass: CPython resolves attribute access on
# exact threading.local instances through a fast C-level code path, while instances of
# subclasses fall back to a slower generic lookup.  The difference is a few ns per
# access — which the hot path pays on every counted flop.
_TLS = threading.local()


def _create_thread_state() -> CountsTarget:
    """Create the calling thread's counting state; returns the fresh ``flop_counts`` alias target.

    Only called when the calling thread has no state yet: from the facade's ``_ensure()``
    and from hot-path ``except AttributeError`` handlers.  Returning the alias target lets
    such a handler initialize the state and still count the triggering operation in a
    single statement.  Threads start with counting unpaused and verbosity off.
    """
    _TLS.flop_counts_active = FlopCounts()
    _TLS.flop_counts_inactive = FlopCounts()
    _TLS.verbosity = Verbosity.OFF
    _TLS.flop_counts = _counting_target()
    return _TLS.flop_counts


def _counting_target() -> CountsTarget:
    """Return what increments go to while the calling thread's counting is not paused.

    That is the thread's plain counts, unless its verbosity level asks for the flops to be
    logged as they are registered, in which case increments are routed through a logging
    stand-in wrapping those same counts.  The stand-in is built here rather than kept on the
    thread: choosing a target happens only when one changes — a context entry or exit, a
    pause, a resume, a reset — never per counted flop.
    """
    if _TLS.verbosity is not Verbosity.INFO:
        return _TLS.flop_counts_active
    return LoggingFlopCounts(_TLS.flop_counts_active)


class ThreadLocalFlopCounter:
    """Facade over the *calling thread's* counting state.

    Every method operates on the calling thread's state only.  All methods here are
    cold-path (see module docstring): they prioritize clarity, going through ``_ensure()``
    plus plain statements.  The ``incr_*`` methods exist for unit tests only; production
    counting sites inline their increments instead.

    The facade itself is stateless — all state lives on the thread-local ``_TLS`` — so
    this single module-level instance is safe to share across threads.
    """

    # -------------------------------------------------------------------------
    #  Pause / Resume / Status API
    # -------------------------------------------------------------------------
    @staticmethod
    def _ensure() -> None:
        """Get-or-create: initialize the calling thread's state if this is its first access."""
        try:
            _TLS.flop_counts  # noqa: B018 -- attribute probe: raises AttributeError on first access
        except AttributeError:
            _create_thread_state()

    def pause(self) -> None:
        self._ensure()
        _TLS.flop_counts = _TLS.flop_counts_inactive

    def resume(self) -> None:
        self._ensure()
        _TLS.flop_counts = _counting_target()

    def reset(self) -> None:
        self._ensure()
        _TLS.flop_counts_active.reset()
        _TLS.flop_counts = _counting_target()  # reset also resumes

    def is_active(self) -> bool:
        self._ensure()
        return _TLS.flop_counts is not _TLS.flop_counts_inactive

    def flop_counts(self) -> FlopCounts:
        self._ensure()
        return _TLS.flop_counts_active.copy()  # single-owner mutation, so the copy is never torn

    def total_count(self) -> int:
        """Shorthand for self.flop_counts().total_count()."""
        self._ensure()
        return _TLS.flop_counts_active.total_count()

    def __getattr__(self, item: str) -> int:
        # provide shorthand access to the counts
        if item in FlopCounts.field_names():
            self._ensure()
            return getattr(_TLS.flop_counts_active, item)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    # -------------------------------------------------------------------------
    #  Verbosity API
    # -------------------------------------------------------------------------
    def verbosity(self) -> Verbosity:
        """Return the calling thread's current verbosity level."""
        self._ensure()
        return _TLS.verbosity

    def set_verbosity(self, level: Verbosity) -> Verbosity:
        """Set the calling thread's verbosity level.

        Args:
            level: Level to switch this thread to.

        Returns:
            The level that was replaced, so the caller can restore it — which is how nested
            counting contexts give the innermost one's level precedence.
        """
        self._ensure()
        previous: Verbosity = _TLS.verbosity
        _TLS.verbosity = level
        if _TLS.flop_counts is not _TLS.flop_counts_inactive:
            _TLS.flop_counts = _counting_target()  # paused threads pick the new target up on resume()
        return previous

    # -------------------------------------------------------------------------
    #  Incrementing counts  (unit tests only -- production counting sites inline
    #  their increments, see module docstring)
    # -------------------------------------------------------------------------
    def incr_abs(self) -> None:
        self._ensure()
        _TLS.flop_counts.ABS += 1

    def incr_minus(self) -> None:
        self._ensure()
        _TLS.flop_counts.MINUS += 1

    def incr_copysign(self) -> None:
        self._ensure()
        _TLS.flop_counts.COPYSIGN += 1

    def incr_comp(self) -> None:
        self._ensure()
        _TLS.flop_counts.COMP += 1

    def incr_rnd(self) -> None:
        self._ensure()
        _TLS.flop_counts.RND += 1

    def incr_f2i(self) -> None:
        self._ensure()
        _TLS.flop_counts.F2I += 1

    def incr_i2f(self) -> None:
        self._ensure()
        _TLS.flop_counts.I2F += 1

    def incr_add(self) -> None:
        self._ensure()
        _TLS.flop_counts.ADD += 1

    def incr_sub(self) -> None:
        self._ensure()
        _TLS.flop_counts.SUB += 1

    def incr_mul(self) -> None:
        self._ensure()
        _TLS.flop_counts.MUL += 1

    def incr_div(self) -> None:
        self._ensure()
        _TLS.flop_counts.DIV += 1

    def incr_fma(self) -> None:
        self._ensure()
        _TLS.flop_counts.FMA += 1

    def incr_sqrt(self) -> None:
        self._ensure()
        _TLS.flop_counts.SQRT += 1

    def incr_cbrt(self) -> None:
        self._ensure()
        _TLS.flop_counts.CBRT += 1

    def incr_exp(self) -> None:
        self._ensure()
        _TLS.flop_counts.EXP += 1

    def incr_exp2(self) -> None:
        self._ensure()
        _TLS.flop_counts.EXP2 += 1

    def incr_exp10(self) -> None:
        self._ensure()
        _TLS.flop_counts.EXP10 += 1

    def incr_log(self) -> None:
        self._ensure()
        _TLS.flop_counts.LOG += 1

    def incr_log2(self) -> None:
        self._ensure()
        _TLS.flop_counts.LOG2 += 1

    def incr_log10(self) -> None:
        self._ensure()
        _TLS.flop_counts.LOG10 += 1

    def incr_pow(self) -> None:
        self._ensure()
        _TLS.flop_counts.POW += 1

    def incr_sin(self) -> None:
        self._ensure()
        _TLS.flop_counts.SIN += 1

    def incr_cos(self) -> None:
        self._ensure()
        _TLS.flop_counts.COS += 1

    def incr_tan(self) -> None:
        self._ensure()
        _TLS.flop_counts.TAN += 1

    def incr_asin(self) -> None:
        self._ensure()
        _TLS.flop_counts.ASIN += 1

    def incr_acos(self) -> None:
        self._ensure()
        _TLS.flop_counts.ACOS += 1

    def incr_atan(self) -> None:
        self._ensure()
        _TLS.flop_counts.ATAN += 1

    def incr_atan2(self) -> None:
        self._ensure()
        _TLS.flop_counts.ATAN2 += 1

    def incr_hypot(self) -> None:
        self._ensure()
        _TLS.flop_counts.HYPOT += 1

    def incr_expm1(self) -> None:
        self._ensure()
        _TLS.flop_counts.EXPM1 += 1

    def incr_log1p(self) -> None:
        self._ensure()
        _TLS.flop_counts.LOG1P += 1

    def incr_fmod(self) -> None:
        self._ensure()
        _TLS.flop_counts.FMOD += 1

    def incr_sinh(self) -> None:
        self._ensure()
        _TLS.flop_counts.SINH += 1

    def incr_cosh(self) -> None:
        self._ensure()
        _TLS.flop_counts.COSH += 1

    def incr_tanh(self) -> None:
        self._ensure()
        _TLS.flop_counts.TANH += 1

    def incr_asinh(self) -> None:
        self._ensure()
        _TLS.flop_counts.ASINH += 1

    def incr_acosh(self) -> None:
        self._ensure()
        _TLS.flop_counts.ACOSH += 1

    def incr_atanh(self) -> None:
        self._ensure()
        _TLS.flop_counts.ATANH += 1


# --- module-level instance through which cold paths access the calling thread's counter ---
THREAD_COUNTER = ThreadLocalFlopCounter()
