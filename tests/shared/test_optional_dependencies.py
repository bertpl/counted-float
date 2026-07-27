import re
import tomllib
from importlib.metadata import distributions, metadata
from pathlib import Path

import pytest

from counted_float._core.compatibility import Capability, MissingCapabilityError
from counted_float._core.compatibility._optional_dependencies import _declared_extras

_PYPROJECT = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"


# =================================================================================================
#  Derived from the declared extras
# =================================================================================================
def test_the_declared_extras_are_read_from_the_installed_metadata():
    # --- arrange -----------------------------------------
    declared = set(metadata("counted-float").get_all("Provides-Extra") or [])

    # --- act / assert ------------------------------------
    assert _declared_extras() == declared


def test_the_declared_extras_match_pyproject_itself():
    # the runtime reads installed metadata; this pins that metadata against the file it is built
    # from, so a stale install cannot make the derivation look right while answering from
    # yesterday's extras
    # --- arrange -----------------------------------------
    declared_in_source = set(tomllib.loads(_PYPROJECT.read_text())["project"]["optional-dependencies"])

    # --- act / assert ------------------------------------
    assert _declared_extras() == declared_in_source


@pytest.mark.parametrize("capability", list(Capability), ids=lambda c: c.name)
def test_every_capability_names_an_extra_the_package_declares(capability):
    # the members are the one packaging fact stated in code: which extra covers which feature.
    # Renaming an extra without updating them would leave a guard naming an install string that no
    # longer resolves.
    # --- act / assert ------------------------------------
    assert capability.value in _declared_extras()


def test_a_capability_can_be_looked_up_by_the_extra_name():
    # --- act / assert ------------------------------------
    assert Capability("cli") is Capability.CLI


def test_an_unknown_extra_name_is_rejected():
    # --- act / assert ------------------------------------
    with pytest.raises(ValueError, match="no-such-extra"):
        Capability("no-such-extra")


def test_required_distributions_are_read_from_the_extra_that_installs_them():
    # --- act / assert ------------------------------------
    assert Capability.CLI.required_distributions() == {"click"}


def test_required_distributions_collapse_an_extra_declared_once_per_python_version():
    # several of these are spelled once per interpreter range; what a caller needs is the set of
    # distributions, not the version-pinned spellings of each
    # --- act ---------------------------------------------
    required = Capability.FLOPS_BENCHMARKING.required_distributions()

    # --- assert ------------------------------------------
    assert required == {"numba", "numpy", "psutil", "py-cpuinfo"}


# =================================================================================================
#  Availability
# =================================================================================================
@pytest.mark.parametrize("capability", list(Capability), ids=lambda c: c.name)
def test_availability_follows_whether_the_distributions_are_installed(capability):
    # the expected value is derived by enumerating the environment rather than by asking about each
    # distribution one at a time, so this stays a check and does not become a second copy of the
    # implementation. Names are normalized per PEP 503, since `py-cpuinfo` and `py_cpuinfo` are one
    # distribution spelled two ways.
    # --- arrange -----------------------------------------
    def normalized(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    installed = {normalized(dist.metadata["Name"]) for dist in distributions()}
    every_one_present = {normalized(name) for name in capability.required_distributions()} <= installed

    # --- act / assert ------------------------------------
    assert capability.is_available() is every_one_present


def test_a_distribution_that_is_not_installed_reads_as_absent():
    # the branch every guard depends on, exercised directly rather than left to whichever CI leg
    # happens to run without an extra
    # --- arrange -----------------------------------------
    from counted_float._core.compatibility._optional_dependencies import _is_installed

    # --- act / assert ------------------------------------
    assert _is_installed("counted-float") is True
    assert _is_installed("no-such-distribution-anywhere") is False


@pytest.mark.parametrize("capability", list(Capability), ids=lambda c: c.name)
def test_the_message_names_the_extra_to_install(capability):
    # --- act ---------------------------------------------
    message = capability.missing_message()

    # --- assert ------------------------------------------
    assert f"counted-float[{capability.value}]" in message


# =================================================================================================
#  required()
# =================================================================================================
def test_required_is_transparent_when_the_capability_is_installed(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(Capability, "is_available", lambda _: True)

    # --- act ---------------------------------------------
    with Capability.CLI.required():
        outcome = "ran"

    # --- assert ------------------------------------------
    assert outcome == "ran"


def test_required_refuses_to_enter_the_block_without_the_extra(monkeypatch):
    # --- arrange -----------------------------------------
    monkeypatch.setattr(Capability, "is_available", lambda _: False)
    entered = False

    # --- act / assert ------------------------------------
    with pytest.raises(MissingCapabilityError, match=r"counted-float\[cli\]"), Capability.CLI.required():
        entered = True  # pragma: no cover -- the guard must raise before the block runs

    assert entered is False


def test_required_lets_a_genuine_error_inside_the_block_surface_as_itself(monkeypatch):
    # a precondition rather than a translated failure: once the extra is known to be present, a
    # problem inside the block is a bug, not a packaging story, and must not be relabelled as one
    # --- arrange -----------------------------------------
    monkeypatch.setattr(Capability, "is_available", lambda _: True)

    # --- act / assert ------------------------------------
    with pytest.raises(ModuleNotFoundError, match="counted_float_no_such_module"), Capability.CLI.required():
        import counted_float_no_such_module  # noqa: F401


def test_missing_capability_is_an_import_error():
    # callers that already catch ImportError around an optional feature keep working
    # --- act / assert ------------------------------------
    assert issubclass(MissingCapabilityError, ImportError)
