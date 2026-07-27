import tomllib
from importlib.metadata import metadata
from pathlib import Path

import pytest

import counted_float._core.compatibility._optional_dependencies as optional_dependencies
from counted_float._core.compatibility import (
    CAP_CLI,
    CAP_FLOPS_BENCHMARKING,
    MissingCapabilityError,
    UnknownCapabilityError,
    capabilities,
    is_available,
    missing_message,
    required_distributions,
    requires,
)

_GUARDED_CAPABILITIES = [CAP_CLI, CAP_FLOPS_BENCHMARKING]
_PYPROJECT = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"


# =================================================================================================
#  Derived from the declared extras
# =================================================================================================
def test_the_capabilities_are_exactly_the_declared_extras():
    # --- arrange -----------------------------------------
    declared = set(metadata("counted-float").get_all("Provides-Extra") or [])

    # --- act / assert ------------------------------------
    assert capabilities() == declared


def test_the_capabilities_match_pyproject_itself():
    # the runtime reads installed metadata; this pins that metadata against the file it is built
    # from, so a stale install cannot make the derivation look right while it is answering from
    # yesterday's extras
    # --- arrange -----------------------------------------
    declared_in_source = set(tomllib.loads(_PYPROJECT.read_text())["project"]["optional-dependencies"])

    # --- act / assert ------------------------------------
    assert capabilities() == declared_in_source


def test_required_distributions_are_read_from_the_extra_that_installs_them():
    # --- act ---------------------------------------------
    for_cli = required_distributions(CAP_CLI)

    # --- assert ------------------------------------------
    assert for_cli == {"click"}


def test_required_distributions_collapse_an_extra_declared_once_per_python_version():
    # the numba requirement is spelled four times, one per interpreter range; what the caller needs
    # is the distribution, not the four version-pinned spellings of it
    # --- act ---------------------------------------------
    for_benchmarking = required_distributions(CAP_FLOPS_BENCHMARKING)

    # --- assert ------------------------------------------
    assert for_benchmarking == {"numba"}


@pytest.mark.parametrize("capability", _GUARDED_CAPABILITIES)
def test_every_guarded_capability_is_actually_declared(capability):
    # the one packaging fact the code states is which extra covers which feature; renaming an extra
    # without updating it would otherwise leave a guard pointing at an install string that no longer
    # resolves
    # --- act / assert ------------------------------------
    assert capability in capabilities()


# =================================================================================================
#  Availability
# =================================================================================================
@pytest.mark.parametrize("capability", _GUARDED_CAPABILITIES)
def test_availability_follows_whether_the_distributions_are_installed(capability):
    # --- arrange -----------------------------------------
    every_one_present = all(
        metadata(name) is not None  # raises PackageNotFoundError when absent
        for name in required_distributions(capability)
    )

    # --- act / assert ------------------------------------
    assert is_available(capability) is every_one_present


def test_a_distribution_that_is_not_installed_reads_as_absent():
    # the branch every guard depends on, exercised directly rather than left to whichever CI leg
    # happens to run without an extra
    # --- act / assert ------------------------------------
    assert optional_dependencies._is_installed("counted-float") is True
    assert optional_dependencies._is_installed("no-such-distribution-anywhere") is False


def test_an_undeclared_capability_is_rejected_rather_than_reported_absent():
    # reporting False would let a typo'd name silently guard nothing at all
    # --- act / assert ------------------------------------
    with pytest.raises(UnknownCapabilityError, match="no-such-extra"):
        is_available("no-such-extra")


def test_the_message_names_the_extra_to_install():
    # --- act ---------------------------------------------
    message = missing_message(CAP_CLI)

    # --- assert ------------------------------------------
    assert f"counted-float[{CAP_CLI}]" in message


# =================================================================================================
#  requires
# =================================================================================================
def test_requires_is_transparent_when_the_capability_is_installed():
    # --- act ---------------------------------------------
    with requires(CAP_CLI):
        outcome = "ran"

    # --- assert ------------------------------------------
    assert outcome == "ran"


def test_requires_refuses_to_enter_the_block_without_the_extra(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(
        "counted_float._core.compatibility._optional_dependencies.is_available",
        lambda _: False,
    )
    entered = False

    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError, match=r"counted-float\[cli\]"), requires(CAP_CLI):
        entered = True  # pragma: no cover -- the guard must raise before the block runs

    assert entered is False


def test_requires_lets_a_genuine_error_inside_the_block_surface_as_itself():
    # a precondition rather than a translated failure: once the extra is known to be present, a
    # problem inside the block is a bug, not a packaging story, and must not be relabelled as one
    # --- act / assert ------------------------------------
    with pytest.raises(ModuleNotFoundError, match="counted_float_no_such_module"), requires(CAP_CLI):
        import counted_float_no_such_module  # noqa: F401


def test_requires_rejects_an_undeclared_capability():
    # --- act / assert ------------------------------------
    with pytest.raises(UnknownCapabilityError), requires("no-such-extra"):
        pass  # pragma: no cover -- the guard must raise before the block runs


def test_missing_capability_is_an_import_error():
    # callers that already catch ImportError around an optional feature keep working
    # --- act / assert ------------------------------------
    assert issubclass(MissingCapabilityError, ImportError)
