import sys
from pathlib import Path

from counted_float._core.counting.verbosity.callsite import UNKNOWN_LOCATION, format_location, locate_call


# ==================================================================================================
#  Locating the caller
# ==================================================================================================
def test_locate_call_reports_the_calling_line():
    # --- act ---------------------------------------------
    location, this_line = locate_call(), sys._getframe().f_lineno  # one line, so both report it

    # --- assert ------------------------------------------
    file_path, line_number = location
    assert Path(file_path).name == "test_callsite.py"
    assert line_number == this_line


def test_locate_call_skips_frames_inside_the_package():
    # --- arrange -----------------------------------------
    # a frame that claims to live in the package, as every counting-machinery frame does.  The
    # angle-bracketed file name keeps coverage from tracing this fabricated code as if it were a
    # source file of its own (it has none on disk).
    package_frame = compile(
        "from counted_float._core.counting.verbosity.callsite import locate_call\nlocation = locate_call()\n",
        "<fabricated counted_float frame>",
        "exec",
    )
    namespace = {"__name__": "counted_float._core.counting.counted_float"}

    # --- act ---------------------------------------------
    exec(package_frame, namespace)  # noqa: S102 -- fabricating a package frame is the point

    # --- assert ------------------------------------------
    assert Path(namespace["location"][0]).name == "test_callsite.py", (
        "The package's own frame should have been walked past, down to this test's frame."
    )


def test_locate_call_skips_the_top_level_package_frame():
    # --- arrange -----------------------------------------
    # a frame whose module name is exactly the package, as ``counted_float/__init__.py`` reports --
    # it lacks the trailing dot the submodule check keys on, so only the exact-name clause skips it.
    package_frame = compile(
        "from counted_float._core.counting.verbosity.callsite import locate_call\nlocation = locate_call()\n",
        "<fabricated counted_float top-level frame>",
        "exec",
    )
    namespace = {"__name__": "counted_float"}

    # --- act ---------------------------------------------
    exec(package_frame, namespace)  # noqa: S102 -- fabricating the top-level package frame is the point

    # --- assert ------------------------------------------
    assert Path(namespace["location"][0]).name == "test_callsite.py", (
        "The top-level package frame should have been walked past, down to this test's frame."
    )


def test_locate_call_without_any_user_frame(monkeypatch):
    # --- arrange -----------------------------------------
    # the walk only gives up when no frame outside the package is left, which a caller of the
    # library never produces -- simulated here by taking the stack away entirely
    monkeypatch.setattr(sys, "_getframe", lambda _depth: None)

    # --- act & assert ------------------------------------
    assert locate_call() == UNKNOWN_LOCATION


# ==================================================================================================
#  Rendering a location
# ==================================================================================================
def test_format_location_keeps_only_the_file_name():
    # --- act & assert ------------------------------------
    assert format_location(("/home/me/proj/my_algo.py", 42)) == "my_algo.py:42"


def test_format_location_of_an_unknown_location():
    # --- act & assert ------------------------------------
    assert format_location(UNKNOWN_LOCATION) == "<unknown>"
