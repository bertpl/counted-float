from importlib.metadata import metadata

import pytest

from counted_float._core.compatibility import (
    CAP_CLI,
    CAP_FLOPS_BENCHMARKING,
    Capability,
    MissingCapabilityError,
    is_importable,
    requires,
)

_ALL_CAPABILITIES = [CAP_CLI, CAP_FLOPS_BENCHMARKING]


# =================================================================================================
#  is_importable
# =================================================================================================
def test_is_importable_true_for_a_module_of_the_standard_library():
    # --- act ---------------------------------------------
    result = is_importable("math")

    # --- assert ------------------------------------------
    assert result is True


def test_is_importable_false_for_a_module_that_does_not_exist():
    # --- act ---------------------------------------------
    result = is_importable("counted_float_no_such_module")

    # --- assert ------------------------------------------
    assert result is False


def test_is_importable_reports_a_module_that_raises_on_import_as_absent(tmp_path, monkeypatch):
    # a distribution can be installed and still unusable -- a broken wheel, an ABI mismatch. What the
    # caller can act on is whether the import works, so an importable-but-raising module reads False.
    # --- arrange -----------------------------------------
    module_name = "counted_float_raises_on_import"
    (tmp_path / f"{module_name}.py").write_text("raise ImportError('deliberately unimportable')\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    # --- act ---------------------------------------------
    result = is_importable(module_name)

    # --- assert ------------------------------------------
    assert result is False


def test_is_importable_caches_its_answer():
    # --- arrange -----------------------------------------
    is_importable("math")

    # --- act ---------------------------------------------
    hits_before = is_importable.cache_info().hits
    is_importable("math")

    # --- assert ------------------------------------------
    assert is_importable.cache_info().hits == hits_before + 1


# =================================================================================================
#  Capability declarations
# =================================================================================================
@pytest.mark.parametrize("capability", _ALL_CAPABILITIES, ids=lambda c: c.extra)
def test_every_capability_names_an_extra_the_package_actually_declares(capability):
    # the extra's name is the one packaging fact these declarations restate, so it is the one that
    # can drift -- renaming it in pyproject without touching this module would leave every guard
    # telling users to install something that no longer exists
    # --- arrange -----------------------------------------
    declared_extras = metadata("counted-float").get_all("Provides-Extra") or []

    # --- act / assert ------------------------------------
    assert capability.extra in declared_extras


@pytest.mark.parametrize("capability", _ALL_CAPABILITIES, ids=lambda c: c.extra)
def test_every_capability_probes_a_module_of_ours(capability):
    # probing one of our own modules rather than a third-party one is what keeps the package list out
    # of the code; a probe pointing elsewhere would quietly reintroduce it
    # --- act / assert ------------------------------------
    assert capability.probe.startswith("counted_float.")


@pytest.mark.parametrize("capability", _ALL_CAPABILITIES, ids=lambda c: c.extra)
def test_the_message_names_the_capability_and_its_install_string(capability):
    # --- act ---------------------------------------------
    message = capability.missing_message()

    # --- assert ------------------------------------------
    assert capability.name in message
    assert f"counted-float[{capability.extra}]" in message


def test_availability_follows_the_probe():
    # --- arrange -----------------------------------------
    absent = Capability(name="Something", extra="something", probe="counted_float_no_such_module")
    present = Capability(name="Something", extra="something", probe="counted_float")

    # --- act / assert ------------------------------------
    assert absent.is_available() is False
    assert present.is_available() is True


# =================================================================================================
#  requires
# =================================================================================================
def test_requires_is_transparent_when_nothing_fails():
    # --- act ---------------------------------------------
    with requires(CAP_CLI):
        outcome = "ran"

    # --- assert ------------------------------------------
    assert outcome == "ran"


def test_requires_turns_a_failed_import_into_install_guidance():
    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError, match=r"counted-float\[cli\]"), requires(CAP_CLI):
        import counted_float_no_such_module  # noqa: F401


def test_requires_chains_the_original_error_rather_than_hiding_it():
    # the guidance answers "what do I install"; the chained cause answers "what was actually missing",
    # which is what makes a genuine bug inside the guarded import still diagnosable
    # --- act ---------------------------------------------
    with pytest.raises(MissingCapabilityError) as excinfo, requires(CAP_FLOPS_BENCHMARKING):
        import counted_float_no_such_module  # noqa: F401

    # --- assert ------------------------------------------
    assert isinstance(excinfo.value.__cause__, ModuleNotFoundError)
    assert excinfo.value.__cause__.name == "counted_float_no_such_module"


def test_requires_lets_unrelated_failures_through():
    # only import problems are a packaging story; anything else must surface as itself
    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="unrelated"), requires(CAP_CLI):
        raise ValueError("unrelated")


def test_missing_capability_is_an_import_error():
    # callers that already catch ImportError around an optional feature keep working
    # --- act / assert ------------------------------------
    assert issubclass(MissingCapabilityError, ImportError)
