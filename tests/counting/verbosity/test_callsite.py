import sys

from counted_float._core.counting.verbosity._callsite import resolve_callsite


# ==================================================================================================
#  Locating the caller
# ==================================================================================================
def test_resolve_callsite_reports_the_calling_line():
    # --- act ---------------------------------------------
    callsite, this_line = resolve_callsite(), sys._getframe().f_lineno  # one line, so both report it

    # --- assert ------------------------------------------
    assert callsite == f"test_callsite.py:{this_line}"


def test_resolve_callsite_skips_frames_inside_the_package():
    # --- arrange -----------------------------------------
    # a frame that claims to live in the package, as every counting-machinery frame does.  The
    # angle-bracketed file name keeps coverage from tracing this fabricated code as if it were a
    # source file of its own (it has none on disk).
    package_frame = compile(
        "from counted_float._core.counting.verbosity._callsite import resolve_callsite\n"
        "callsite = resolve_callsite()\n",
        "<fabricated counted_float frame>",
        "exec",
    )
    namespace = {"__name__": "counted_float._core.counting._counted_float"}

    # --- act ---------------------------------------------
    exec(package_frame, namespace)  # noqa: S102 -- fabricating a package frame is the point

    # --- assert ------------------------------------------
    assert namespace["callsite"].startswith("test_callsite.py:"), (
        "The package's own frame should have been walked past, down to this test's frame."
    )


def test_resolve_callsite_without_any_user_frame(monkeypatch):
    # --- arrange -----------------------------------------
    # the walk only gives up when no frame outside the package is left, which a caller of the
    # library never produces -- simulated here by taking the stack away entirely
    monkeypatch.setattr(sys, "_getframe", lambda _depth: None)

    # --- act ---------------------------------------------
    callsite = resolve_callsite()

    # --- assert ------------------------------------------
    assert callsite == "<unknown>"
