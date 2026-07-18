"""Thread-local flop-counting state.

Each OS thread owns two FlopCounts objects, created lazily on its first counted operation
(or first cold-path access):

  - ``live``    : the thread's real counts (what contexts snapshot and diff)
  - ``discard`` : a sink used while counting is paused

``counts`` is an alias pointing at one of the two.  The hot path is therefore unconditionally
``_TLS.counts.<FIELD> += 1`` — branch-free whether paused or not (successor of the global
counter's 0/1 increment multiplier, minus one attribute load and the method call).
pause()/resume() just swap the alias.

Hot paths (CountedFloat dunders, math.* replacements) inline the increment and MUST NOT call
methods on THREAD_COUNTER, which is a cold-path facade only.  State lives on ``_TLS``; the
facade itself is stateless, so a single module instance is safe to share across threads.

Robustness note: ``contextvars`` measured faster per increment but was rejected — new threads
start with an empty context and asyncio runs callbacks in context *copies*, so lazily-set
state can fail to escape ``Context.run()``, making count attribution depend on task-creation
order (and context propagation into worker threads would share mutable state across threads).
threading.local has exactly one unambiguous semantic: one state per OS thread.
"""

from __future__ import annotations

import threading

from counted_float._core.models import FlopCounts

# bare threading.local on purpose: CPython's local_getattro has a fast path for the exact
# _thread._local type; subclasses take the slower generic route
_TLS = threading.local()


def _init_thread_state() -> FlopCounts:
    """Create this thread's counting state; returns the active ``counts`` target.

    Called from hot-path ``except AttributeError`` handlers (first counted op on a thread)
    and from the facade's ensure-step.  Threads start unpaused.
    """
    live = FlopCounts()
    _TLS.live = live
    _TLS.discard = FlopCounts()
    _TLS.counts = live
    return live


class ThreadLocalFlopCounter:
    """Cold-path facade over the *calling thread's* counting state.

    API-compatible with the previous process-global counter (pause/resume/reset/is_active/
    flop_counts/total_count/field shorthand/incr_*), but every method operates on the calling
    thread only.  The incr_* methods exist for tests and cold call sites; hot paths inline
    the increment instead.
    """

    # -------------------------------------------------------------------------
    #  Pause / Resume / Status API
    # -------------------------------------------------------------------------
    @staticmethod
    def _ensure() -> None:
        """Initialize the calling thread's state if this is its first access."""
        try:
            _TLS.counts  # noqa: B018 -- attribute probe: raises AttributeError on first access
        except AttributeError:
            _init_thread_state()

    def pause(self) -> None:
        self._ensure()
        _TLS.counts = _TLS.discard

    def resume(self) -> None:
        self._ensure()
        _TLS.counts = _TLS.live

    def reset(self) -> None:
        self._ensure()
        _TLS.live.reset()
        _TLS.counts = _TLS.live  # reset also resumes, matching prior behavior

    def is_active(self) -> bool:
        self._ensure()
        return _TLS.counts is _TLS.live

    def flop_counts(self) -> FlopCounts:
        self._ensure()
        return _TLS.live.copy()  # single-owner mutation, so the copy is never torn

    def total_count(self) -> int:
        """Shorthand for self.flop_counts().total_count()."""
        self._ensure()
        return _TLS.live.total_count()

    def __getattr__(self, item: str) -> int:
        # provide shorthand access to the counts
        if item in FlopCounts.field_names():
            self._ensure()
            return getattr(_TLS.live, item)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    # -------------------------------------------------------------------------
    #  Incrementing counts
    # -------------------------------------------------------------------------
    def incr_abs(self) -> None:
        try:
            _TLS.counts.ABS += 1
        except AttributeError:
            _init_thread_state().ABS += 1

    def incr_minus(self) -> None:
        try:
            _TLS.counts.MINUS += 1
        except AttributeError:
            _init_thread_state().MINUS += 1

    def incr_copysign(self) -> None:
        try:
            _TLS.counts.COPYSIGN += 1
        except AttributeError:
            _init_thread_state().COPYSIGN += 1

    def incr_comp(self) -> None:
        try:
            _TLS.counts.COMP += 1
        except AttributeError:
            _init_thread_state().COMP += 1

    def incr_rnd(self) -> None:
        try:
            _TLS.counts.RND += 1
        except AttributeError:
            _init_thread_state().RND += 1

    def incr_f2i(self) -> None:
        try:
            _TLS.counts.F2I += 1
        except AttributeError:
            _init_thread_state().F2I += 1

    def incr_i2f(self) -> None:
        try:
            _TLS.counts.I2F += 1
        except AttributeError:
            _init_thread_state().I2F += 1

    def incr_add(self) -> None:
        try:
            _TLS.counts.ADD += 1
        except AttributeError:
            _init_thread_state().ADD += 1

    def incr_sub(self) -> None:
        try:
            _TLS.counts.SUB += 1
        except AttributeError:
            _init_thread_state().SUB += 1

    def incr_mul(self) -> None:
        try:
            _TLS.counts.MUL += 1
        except AttributeError:
            _init_thread_state().MUL += 1

    def incr_div(self) -> None:
        try:
            _TLS.counts.DIV += 1
        except AttributeError:
            _init_thread_state().DIV += 1

    def incr_fma(self) -> None:
        try:
            _TLS.counts.FMA += 1
        except AttributeError:
            _init_thread_state().FMA += 1

    def incr_sqrt(self) -> None:
        try:
            _TLS.counts.SQRT += 1
        except AttributeError:
            _init_thread_state().SQRT += 1

    def incr_cbrt(self) -> None:
        try:
            _TLS.counts.CBRT += 1
        except AttributeError:
            _init_thread_state().CBRT += 1

    def incr_exp(self) -> None:
        try:
            _TLS.counts.EXP += 1
        except AttributeError:
            _init_thread_state().EXP += 1

    def incr_exp2(self) -> None:
        try:
            _TLS.counts.EXP2 += 1
        except AttributeError:
            _init_thread_state().EXP2 += 1

    def incr_exp10(self) -> None:
        try:
            _TLS.counts.EXP10 += 1
        except AttributeError:
            _init_thread_state().EXP10 += 1

    def incr_log(self) -> None:
        try:
            _TLS.counts.LOG += 1
        except AttributeError:
            _init_thread_state().LOG += 1

    def incr_log2(self) -> None:
        try:
            _TLS.counts.LOG2 += 1
        except AttributeError:
            _init_thread_state().LOG2 += 1

    def incr_log10(self) -> None:
        try:
            _TLS.counts.LOG10 += 1
        except AttributeError:
            _init_thread_state().LOG10 += 1

    def incr_pow(self) -> None:
        try:
            _TLS.counts.POW += 1
        except AttributeError:
            _init_thread_state().POW += 1

    def incr_sin(self) -> None:
        try:
            _TLS.counts.SIN += 1
        except AttributeError:
            _init_thread_state().SIN += 1

    def incr_cos(self) -> None:
        try:
            _TLS.counts.COS += 1
        except AttributeError:
            _init_thread_state().COS += 1

    def incr_tan(self) -> None:
        try:
            _TLS.counts.TAN += 1
        except AttributeError:
            _init_thread_state().TAN += 1

    def incr_asin(self) -> None:
        try:
            _TLS.counts.ASIN += 1
        except AttributeError:
            _init_thread_state().ASIN += 1

    def incr_acos(self) -> None:
        try:
            _TLS.counts.ACOS += 1
        except AttributeError:
            _init_thread_state().ACOS += 1

    def incr_atan(self) -> None:
        try:
            _TLS.counts.ATAN += 1
        except AttributeError:
            _init_thread_state().ATAN += 1

    def incr_atan2(self) -> None:
        try:
            _TLS.counts.ATAN2 += 1
        except AttributeError:
            _init_thread_state().ATAN2 += 1

    def incr_hypot(self) -> None:
        try:
            _TLS.counts.HYPOT += 1
        except AttributeError:
            _init_thread_state().HYPOT += 1

    def incr_expm1(self) -> None:
        try:
            _TLS.counts.EXPM1 += 1
        except AttributeError:
            _init_thread_state().EXPM1 += 1

    def incr_log1p(self) -> None:
        try:
            _TLS.counts.LOG1P += 1
        except AttributeError:
            _init_thread_state().LOG1P += 1

    def incr_fmod(self) -> None:
        try:
            _TLS.counts.FMOD += 1
        except AttributeError:
            _init_thread_state().FMOD += 1

    def incr_sinh(self) -> None:
        try:
            _TLS.counts.SINH += 1
        except AttributeError:
            _init_thread_state().SINH += 1

    def incr_cosh(self) -> None:
        try:
            _TLS.counts.COSH += 1
        except AttributeError:
            _init_thread_state().COSH += 1

    def incr_tanh(self) -> None:
        try:
            _TLS.counts.TANH += 1
        except AttributeError:
            _init_thread_state().TANH += 1

    def incr_asinh(self) -> None:
        try:
            _TLS.counts.ASINH += 1
        except AttributeError:
            _init_thread_state().ASINH += 1

    def incr_acosh(self) -> None:
        try:
            _TLS.counts.ACOSH += 1
        except AttributeError:
            _init_thread_state().ACOSH += 1

    def incr_atanh(self) -> None:
        try:
            _TLS.counts.ATANH += 1
        except AttributeError:
            _init_thread_state().ATANH += 1


# --- module-level instance through which cold paths access the calling thread's counter ---
THREAD_COUNTER = ThreadLocalFlopCounter()
