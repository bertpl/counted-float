"""Concurrency battery for per-thread flop counting.

Each test pins one guarantee of the thread-local design: exact per-thread attribution,
non-interference of background threads, per-thread pause, owner confinement of the context
managers, and race-free math-patch bookkeeping.
"""

import math
import threading
from concurrent.futures import ThreadPoolExecutor

from counted_float import CountedFloat, FlopCountingContext, PauseFlopCounting
from counted_float._core.models import FlopCounts


# ==================================================================================================
#  Exact per-thread attribution
# ==================================================================================================
def test_concurrent_contexts_report_exactly_their_own_counts():
    # --- arrange -----------------------------------------
    # each worker performs a distinct, known op mix; every context must report exactly its own
    n_threads = 4
    barrier = threading.Barrier(n_threads)
    results: dict[int, FlopCounts] = {}

    def worker(idx: int) -> None:
        n_adds = 1_000 * (idx + 1)
        n_muls = 100 * idx
        with FlopCountingContext() as ctx:
            barrier.wait()  # maximize overlap between the workers
            x = CountedFloat(1.5)
            for _ in range(n_adds):
                x = x + 1.0
            for _ in range(n_muls):
                x = x * 0.5  # not an identity constant: * 1.0 would fold away and count nothing
        results[idx] = ctx.flop_counts()

    # --- act ---------------------------------------------
    threads = [threading.Thread(target=worker, args=(idx,)) for idx in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # --- assert ------------------------------------------
    for idx in range(n_threads):
        assert results[idx] == FlopCounts(ADD=1_000 * (idx + 1), MUL=100 * idx), (
            f"thread {idx} must report exactly its own op mix"
        )


def test_context_unaffected_by_background_thread_without_context():
    # --- arrange -----------------------------------------
    # a context counting exactly K ADDs must not absorb a context-less background thread's ops
    k = 5_000
    stop = threading.Event()

    def background_hammer() -> None:
        y = CountedFloat(2.0)
        while not stop.is_set():
            y = y * 1.0 + 0.5

    t = threading.Thread(target=background_hammer)
    t.start()

    # --- act ---------------------------------------------
    try:
        with FlopCountingContext() as ctx:
            x = CountedFloat(1.0)
            for _ in range(k):
                x = x + 1.0
    finally:
        stop.set()
        t.join()

    # --- assert ------------------------------------------
    assert ctx.flop_counts() == FlopCounts(ADD=k), "background thread's ops must not leak into the context"


def test_stress_exact_counts_under_many_threads():
    # --- arrange -----------------------------------------
    # 8 threads x 20k ops each, all overlapping: every per-thread count must stay exact
    # (doubles as the free-threaded correctness gate when run on such builds)
    n_threads = 8
    n_ops = 20_000
    barrier = threading.Barrier(n_threads)

    def worker(idx: int) -> FlopCounts:
        with FlopCountingContext() as ctx:
            barrier.wait()
            x = CountedFloat(1.0)
            for _ in range(n_ops):
                x = x + 1.0
        return ctx.flop_counts()

    # --- act ---------------------------------------------
    with ThreadPoolExecutor(max_workers=n_threads) as ex:
        all_counts = list(ex.map(worker, range(n_threads)))

    # --- assert ------------------------------------------
    assert all(counts == FlopCounts(ADD=n_ops) for counts in all_counts)
    total = sum(all_counts, FlopCounts())
    assert total == FlopCounts(ADD=n_threads * n_ops)


# ==================================================================================================
#  Per-thread pause
# ==================================================================================================
def test_pause_flop_counting_affects_calling_thread_only():
    # --- arrange -----------------------------------------
    ready = threading.Event()
    release = threading.Event()
    observed: dict[str, FlopCounts] = {}

    def worker() -> None:
        with FlopCountingContext() as ctx:
            ready.wait()  # main thread is paused now
            x = CountedFloat(1.0)
            for _ in range(100):
                x = x + 1.0
            release.set()
        observed["worker"] = ctx.flop_counts()

    t = threading.Thread(target=worker)
    t.start()

    # --- act ---------------------------------------------
    with FlopCountingContext() as ctx_main, PauseFlopCounting():
        ready.set()
        release.wait()  # worker counted its ops while this thread was paused
        y = CountedFloat(2.0)
        _ = y * y  # paused on this thread: not counted
    t.join()

    # --- assert ------------------------------------------
    assert observed["worker"] == FlopCounts(ADD=100), "a paused main thread must not pause other threads"
    assert ctx_main.flop_counts() == FlopCounts(), "ops during pause on the pausing thread must not count"


# ==================================================================================================
#  Owner confinement
# ==================================================================================================
def _call_in_thread(fn) -> BaseException | None:
    """Run fn() on a fresh thread; returns the exception it raised, if any."""
    caught: list[BaseException] = []

    def runner() -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 -- test helper: capture anything to re-inspect
            caught.append(exc)

    t = threading.Thread(target=runner)
    t.start()
    t.join()
    return caught[0] if caught else None


def test_open_context_is_confined_to_owner_thread():
    # --- arrange -----------------------------------------
    with FlopCountingContext() as ctx:
        # --- act -----------------------------------------
        exc_read = _call_in_thread(ctx.flop_counts)
        exc_pause = _call_in_thread(ctx.pause)
        exc_enter = _call_in_thread(ctx.__enter__)
        exc_exit = _call_in_thread(lambda: ctx.__exit__(None, None, None))

    # --- assert ------------------------------------------
    for exc in (exc_read, exc_pause, exc_enter, exc_exit):
        assert isinstance(exc, RuntimeError), "cross-thread use of an open context must raise RuntimeError"
        assert "confined to the thread" in str(exc)


def test_closed_context_is_reusable_from_another_thread():
    # --- arrange -----------------------------------------
    ctx = FlopCountingContext()
    with ctx:
        _ = CountedFloat(1.0) + 1.0
    counts_after_first = ctx.flop_counts()

    # --- act ---------------------------------------------
    # sequential reuse of one instance across threads keeps working (subtotal accumulates)
    def reuse() -> None:
        with ctx:
            x = CountedFloat(1.0)
            _ = x * 2.0

    exc = _call_in_thread(reuse)

    # --- assert ------------------------------------------
    assert exc is None
    assert counts_after_first == FlopCounts(ADD=1)
    assert ctx.flop_counts() == FlopCounts(ADD=1, MUL=1)


def test_closed_context_flop_counts_readable_from_any_thread():
    # --- arrange -----------------------------------------
    with FlopCountingContext() as ctx:
        _ = CountedFloat(1.0) + 1.0

    # --- act ---------------------------------------------
    observed: dict[str, FlopCounts] = {}
    exc = _call_in_thread(lambda: observed.update(counts=ctx.flop_counts()))

    # --- assert ------------------------------------------
    assert exc is None, "a closed context's counts are frozen and safe to read from any thread"
    assert observed["counts"] == FlopCounts(ADD=1)


def test_pause_flop_counting_exit_confined_to_owner_thread():
    # --- arrange -----------------------------------------
    pause = PauseFlopCounting()
    pause.__enter__()

    # --- act ---------------------------------------------
    exc = _call_in_thread(lambda: pause.__exit__(None, None, None))

    # --- assert ------------------------------------------
    assert isinstance(exc, RuntimeError), "cross-thread exit of PauseFlopCounting must raise RuntimeError"
    pause.__exit__(None, None, None)  # owner thread can still exit properly


# ==================================================================================================
#  Math-patch bookkeeping under concurrency
# ==================================================================================================
def test_patch_refcount_survives_concurrent_context_churn():
    # --- arrange -----------------------------------------
    from counted_float._core.counting import math_patching

    sqrt_before = math.sqrt
    n_threads = 8
    barrier = threading.Barrier(n_threads)

    def churn() -> None:
        barrier.wait()
        for _ in range(200):
            with FlopCountingContext():
                _ = math.sqrt(CountedFloat(2.0))

    # --- act ---------------------------------------------
    threads = [threading.Thread(target=churn) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # --- assert ------------------------------------------
    assert math.sqrt is sqrt_before, "after all contexts closed, math.sqrt must be restored"
    assert math_patching._active_context_count == 0
