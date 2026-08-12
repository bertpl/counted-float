import math
import threading

import pytest

from counted_float import CountedFloat, FlopCountingContext, PauseFlopCounting, Verbosity
from counted_float._core.counting import math_patching

UNCOUNTED_FUNCTION_NAMES = sorted(math_patching._UNCOUNTED_MATH)

# what each of them needs after its first (counted) argument
EXTRA_ARGUMENTS = {"ldexp": (2,), "nextafter": (3.0,)}


# ==================================================================================================
#  What gets reported
# ==================================================================================================
@pytest.mark.parametrize("function_name", UNCOUNTED_FUNCTION_NAMES)
def test_every_uncounted_math_function_is_reported(logged_lines, function_name):
    # --- arrange -----------------------------------------
    arguments = (CountedFloat(2.5), *EXTRA_ARGUMENTS.get(function_name, ()))

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        # resolved inside the context, where the replacements are installed
        getattr(math, function_name)(*arguments)

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert line.split()[:2] == ["WARN", function_name]


def test_isclose_is_counted_not_reported(logged_lines):
    # isclose graduated from the uncounted list: it counts its deterministic core, so at WARNING
    # verbosity a counted isclose call must produce no report -- a CountedFloat tolerance
    # arriving by keyword counts the call exactly like a positional operand
    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING) as ctx:
        _ = math.isclose(CountedFloat(2.0), 2.5)
        _ = math.isclose(2.0, 2.5, rel_tol=CountedFloat(0.1))

    # --- assert ------------------------------------------
    assert logged_lines() == []
    assert ctx.flop_counts().SUB == 2


@pytest.mark.skipif(not hasattr(math, "sumprod"), reason="math.sumprod exists from Python 3.12")
def test_sumprod_is_counted_not_reported(logged_lines):
    # sumprod graduated from the uncounted list: at WARNING verbosity (which stays silent about
    # counted flops) a counted sumprod call must produce no report at all
    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING) as ctx:
        result = math.sumprod((CountedFloat(v) for v in (1.0, 2.0)), (v for v in (3.0, 4.0)))

    # --- assert ------------------------------------------
    assert logged_lines() == []
    assert float(result) == 11.0
    assert ctx.flop_counts().SUMPROD == 1


def test_a_call_without_counted_values_is_not_reported(logged_lines):
    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        _ = math.ulp(2.5)

    # --- assert ------------------------------------------
    assert logged_lines() == [], "Nothing was counted, but nothing was countable either."


def test_the_original_result_is_returned(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        ulp = math.ulp(x)
        mantissa, exponent = math.frexp(x)

    # --- assert ------------------------------------------
    assert ulp == math.ulp(2.5)
    assert (mantissa, exponent) == math.frexp(2.5)


def test_reported_calls_are_not_counted():
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING) as ctx:
        _ = math.ulp(x)

    # --- assert ------------------------------------------
    assert ctx.flop_counts().total_count() == 0, "Reporting an uncounted call must not invent a count."


# ==================================================================================================
#  Levels
# ==================================================================================================
def test_off_reports_nothing(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext():
        _ = math.ulp(x)

    # --- assert ------------------------------------------
    assert logged_lines() == []


def test_a_call_while_paused_is_not_reported(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING), PauseFlopCounting():
        _ = math.ulp(x)

    # --- assert ------------------------------------------
    assert logged_lines() == [], (
        "Paused operations are deliberately uncounted, so an uncountable one is nothing to warn about."
    )


def test_warning_does_not_log_counted_flops(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        _ = x * x
        _ = math.ulp(x)

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert line.startswith("WARN"), "WARNING reports what could not be counted, not what could."


def test_info_reports_uncounted_calls_too(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.INFO):
        _ = x * x
        _ = math.ulp(x)

    # --- assert ------------------------------------------
    counted, uncounted = logged_lines()
    assert counted.split()[:2] == ["INFO", "MUL"]
    assert uncounted.split()[:2] == ["WARN", "ulp"]


# ==================================================================================================
#  Deduplication
# ==================================================================================================
def test_one_call_site_is_reported_once(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        for _ in range(5):
            _ = math.ulp(x)

    # --- assert ------------------------------------------
    assert len(logged_lines()) == 1, "A warning in a loop should be reported once, not per iteration."


def test_each_call_site_is_reported_separately(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        _ = math.ulp(x)
        _ = math.ulp(x)

    # --- assert ------------------------------------------
    first, second = logged_lines()
    assert first != second, "Two distinct call sites are two distinct findings."


def test_two_operations_from_one_call_site_are_both_reported(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        _ = math.ulp(x), math.frexp(x)  # two operations, one source line -> one shared location

    # --- assert ------------------------------------------
    operations = {line.split()[1] for line in logged_lines()}
    assert operations == {"ulp", "frexp"}, (
        "The operation is half the dedup key, so two operations from one line are two findings."
    )


def test_a_call_site_is_reported_once_per_process(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    def run() -> None:
        with FlopCountingContext(verbosity=Verbosity.WARNING):
            _ = math.ulp(x)

    # --- act ---------------------------------------------
    run()
    run()

    # --- assert ------------------------------------------
    assert len(logged_lines()) == 1, "A finding belongs to a source line, so once is enough."


# ==================================================================================================
#  Threads
# ==================================================================================================
def test_a_thread_that_never_counted_reports_nothing(logged_lines):
    # --- arrange -----------------------------------------
    # the math module is patched process-wide, so another thread meets the replacements too --
    # while holding no verbosity state of its own to report through
    x = CountedFloat(2.5)
    results: list[float] = []

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        worker = threading.Thread(target=lambda: results.append(math.ulp(x)))
        worker.start()
        worker.join()

    # --- assert ------------------------------------------
    assert results == [math.ulp(2.5)]
    assert logged_lines() == []


def test_reporting_survives_another_reporting_thread_finishing(logged_lines):
    # --- arrange -----------------------------------------
    # the replacements are installed while *any* thread reports, so one reporting thread
    # finishing must leave them in place for another that is still reporting
    x = CountedFloat(2.5)
    original_ulp = math.ulp
    worker_is_reporting = threading.Event()
    worker_may_finish = threading.Event()

    def worker() -> None:
        with FlopCountingContext(verbosity=Verbosity.WARNING):
            worker_is_reporting.set()
            assert worker_may_finish.wait(timeout=5)
            _ = math.ulp(x)  # called after the other reporting thread has come and gone

    # --- act ---------------------------------------------
    thread = threading.Thread(target=worker)
    thread.start()
    assert worker_is_reporting.wait(timeout=5)
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        pass  # a second reporting thread comes and goes
    still_installed = math.ulp is math_patching._UNCOUNTED_PATCHES["ulp"]
    worker_may_finish.set()
    thread.join()

    # --- assert ------------------------------------------
    assert still_installed, "The worker was still reporting, so the replacements must stay installed."
    (line,) = logged_lines()
    assert line.split()[:2] == ["WARN", "ulp"]
    assert math.ulp is original_ulp, "The last reporting thread finishing restores the original."


# ==================================================================================================
#  Patch lifecycle — installed only while a thread is reporting
# ==================================================================================================
@pytest.mark.parametrize("function_name", UNCOUNTED_FUNCTION_NAMES)
def test_not_patched_at_the_default_verbosity(function_name):
    # --- arrange -----------------------------------------
    original = getattr(math, function_name)

    # --- act & assert ------------------------------------
    with FlopCountingContext():
        assert getattr(math, function_name) is original, (
            "A context that reports nothing has no reason to route these calls through a wrapper."
        )


@pytest.mark.parametrize("function_name", UNCOUNTED_FUNCTION_NAMES)
def test_patched_while_reporting_and_restored_after(function_name):
    # --- arrange -----------------------------------------
    original = getattr(math, function_name)

    # --- act & assert ------------------------------------
    with FlopCountingContext():
        with FlopCountingContext(verbosity=Verbosity.WARNING):
            assert getattr(math, function_name) is math_patching._UNCOUNTED_PATCHES[function_name]
        # the enclosing context is still open, but nobody is reporting through it any more
        assert getattr(math, function_name) is original
    assert getattr(math, function_name) is original


def test_a_silent_context_nested_in_a_reporting_one_suspends_reporting(logged_lines):
    # --- arrange -----------------------------------------
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        with FlopCountingContext():
            _ = math.ulp(x)
        _ = math.nextafter(x, 3.0)

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert "nextafter" in line, "The silent inner context should have suspended reporting entirely."


def test_reporting_refcount_survives_concurrent_context_churn():
    # --- arrange -----------------------------------------
    # the reporting analog of the counting patches' churn test: its refcount shares the lock but
    # is its own counter, so it gets its own hammer
    ulp_before = math.ulp
    x = CountedFloat(2.5)
    n_threads = 8
    barrier = threading.Barrier(n_threads)

    def churn() -> None:
        barrier.wait()
        for _ in range(200):
            with FlopCountingContext(verbosity=Verbosity.WARNING):
                _ = math.ulp(x)  # exercise the replacement itself while patches churn

    # --- act ---------------------------------------------
    threads = [threading.Thread(target=churn) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # --- assert ------------------------------------------
    assert math.ulp is ulp_before, "after the last reporting context closed, math.ulp must be restored"
    assert math_patching._reporting_thread_count == 0
    assert math_patching._active_context_count == 0


def test_replacements_delegate_to_what_they_displaced():
    # --- arrange -----------------------------------------
    # the same property the counting replacements' snapshot carries: a replacement must delegate
    # to the function it replaced, never to a stale reference
    originals = {name: getattr(math, name) for name in UNCOUNTED_FUNCTION_NAMES}

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        captured = dict(math_patching._uncounted_originals)

    # --- assert ------------------------------------------
    assert captured == originals


def test_the_two_patch_sets_are_disjoint():
    # --- arrange -----------------------------------------
    # they patch the same module, so an overlap would mean one silently overriding the other
    counting = set(math_patching._PATCHES)
    reporting = set(math_patching._UNCOUNTED_PATCHES)

    # --- act & assert ------------------------------------
    assert counting & reporting == set()
    assert "sqrt" in counting, "Sanity check that the counting set is the one being compared against."


@pytest.mark.parametrize("function_name", UNCOUNTED_FUNCTION_NAMES)
def test_uncounted_functions_exist_in_math(function_name):
    # --- act & assert ------------------------------------
    assert callable(getattr(math, function_name))


# ==================================================================================================
#  The wrapper factory itself
# ==================================================================================================
# Direct tests of _make_uncounted_wrapper: the module-level _UNCOUNTED_PATCHES registry is built at
# import time, so only a factory call made inside a test exercises the closure where mutation
# attribution can see it. Each test builds its own probe name -- warnings dedup per (operation,
# location) process-wide, so sharing a name across tests would silence all but the first.
@pytest.fixture
def make_probe_wrapper(monkeypatch):
    """Build wrappers for fake math functions that record their delegated calls.

    Removing the reporting patches restores everything in _uncounted_originals onto the math
    module, so a probe entry leaks a new `math.<probe>` attribute the monkeypatch teardown does
    not know about; the fixture deletes those on the way out.
    """
    probe_names: list[str] = []

    def make(name: str, delegate_calls: list):
        def original(*args: object, **kwargs: object) -> str:
            delegate_calls.append((args, kwargs))
            return "delegated"

        monkeypatch.setitem(math_patching._uncounted_originals, name, original)
        probe_names.append(name)
        return math_patching._make_uncounted_wrapper(name, f"{name} consequence")

    yield make
    for name in probe_names:
        if hasattr(math, name):
            delattr(math, name)


def test_a_wrapper_delegates_untouched_when_nobody_reports(make_probe_wrapper, logged_lines):
    # --- arrange -----------------------------------------
    delegate_calls: list = []
    wrapper = make_probe_wrapper("probe_silent", delegate_calls)
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    result = wrapper(x, key=x)  # no context open anywhere: the thread is not reporting

    # --- assert ------------------------------------------
    assert result == "delegated"
    assert delegate_calls == [((x,), {"key": x})]
    assert logged_lines() == []


def test_a_wrapper_stays_silent_for_plain_arguments_while_reporting(make_probe_wrapper, logged_lines):
    # --- arrange -----------------------------------------
    delegate_calls: list = []
    wrapper = make_probe_wrapper("probe_plain", delegate_calls)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        result = wrapper(2.5, key=1.5)

    # --- assert ------------------------------------------
    assert result == "delegated"
    assert delegate_calls == [((2.5,), {"key": 1.5})]
    assert logged_lines() == [], "Nothing countable was involved, so there is nothing to warn about."


def test_a_wrapper_reports_its_name_and_consequence_for_counted_arguments(make_probe_wrapper, logged_lines):
    # --- arrange -----------------------------------------
    delegate_calls: list = []
    wrapper = make_probe_wrapper("probe_counted", delegate_calls)
    x = CountedFloat(2.5)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        result = wrapper(x)

    # --- assert ------------------------------------------
    assert result == "delegated"
    assert delegate_calls == [((x,), {})]
    (line,) = logged_lines()
    assert line.split()[:2] == ["WARN", "probe_counted"]
    assert "probe_counted consequence" in line


def test_a_wrapper_detects_a_counted_value_arriving_by_keyword(make_probe_wrapper, logged_lines):
    # --- arrange -----------------------------------------
    delegate_calls: list = []
    wrapper = make_probe_wrapper("probe_keyword", delegate_calls)

    # --- act ---------------------------------------------
    with FlopCountingContext(verbosity=Verbosity.WARNING):
        wrapper(2.5, key=CountedFloat(1.5))

    # --- assert ------------------------------------------
    (line,) = logged_lines()
    assert line.split()[:2] == ["WARN", "probe_keyword"]
