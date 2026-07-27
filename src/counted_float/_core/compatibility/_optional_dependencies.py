"""Optional capabilities, derived from the extras this package declares.

A **capability** is an extra. `pyproject.toml` is the single source of truth for what capabilities
exist and what each one needs, and this module reads that back from the installed distribution's own
metadata rather than restating any of it:

- `Provides-Extra` -> the extras that exist
- the ``extra == '<name>'`` markers on `Requires-Dist` -> the distributions each one installs

So adding a package to an extra needs no change here, and renaming an extra cannot leave a guard
telling users to install something that no longer resolves. The enum members below are the one thing
metadata cannot supply — which part of *this* codebase each extra covers — and a test pins every
member's value against the declared extras.

**What is checked is installation, not importability.** Testing an import needs a module name, but
the metadata records distribution names, and the two are not the same — the `py-cpuinfo`
distribution installs a module called `cpuinfo`. Translating one to the other is only possible by
inspecting an installed package, so it cannot be done for the packages this is asked about: the
absent ones. Installation is what remains answerable, and the cost is that a distribution which is
installed but broken reads as available.

Someone who acquires a package by a route other than our extra is unaffected — it is installed
either way, which is the case that matters.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from functools import cache
from importlib.metadata import PackageNotFoundError, distribution, metadata

_DISTRIBUTION_NAME = "counted-float"

# `numpy>=2.1; (python_version == '3.13') and extra == 'benchmarking'` -> name `numpy`, extra
# `benchmarking`. Version specifiers and environment markers are deliberately dropped: this answers
# "is it here", and a marker would make the answer depend on the interpreter rather than the install.
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_EXTRA_MARKER = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")


class MissingCapabilityError(ImportError):
    """A capability was reached without the extra that makes it work."""


# =================================================================================================
#  Capability
# =================================================================================================
class Capability(StrEnum):
    """A part of this package that only works when its extra is installed.

    The value is the extra's name as declared in `pyproject.toml`, so ``Capability("cli")`` resolves
    a member and an unknown name raises `ValueError` — while ``Capability.CLI`` is spelled out, and
    a typo in it fails at import rather than whenever the guarded branch happens to run.
    """

    CLI = "cli"
    FLOPS_BENCHMARKING = "numba"

    # -------------------------------------------------------------------------
    #  Main API
    # -------------------------------------------------------------------------
    def is_available(self) -> bool:
        """Whether every distribution this capability needs is installed."""
        return all(_is_installed(name) for name in self.required_distributions())

    @contextmanager
    def required(self) -> Iterator[None]:
        """Refuse to enter the block unless this capability is installed, naming what to install.

        A precondition rather than a rescued failure: the block runs only once the extra is known to
        be there, so a genuine error inside it surfaces as itself instead of being relabelled as a
        packaging problem.
        """
        if not self.is_available():
            raise MissingCapabilityError(self.missing_message())

        yield

    def missing_message(self) -> str:
        """The actionable install line shown when this capability is reached without its extra."""
        return f'This feature requires the "{self}" extra: pip install "{_DISTRIBUTION_NAME}[{self}]"'

    def required_distributions(self) -> frozenset[str]:
        """The distributions this capability needs, as named by the extra that installs them."""
        return _required_distributions(self)


# =================================================================================================
#  Reading the installed metadata
# =================================================================================================
@cache
def _declared_extras() -> frozenset[str]:
    """Every extra this package declares, i.e. every capability it can be installed with."""
    return frozenset(metadata(_DISTRIBUTION_NAME).get_all("Provides-Extra") or ())


@cache
def _required_distributions(extra: str) -> frozenset[str]:
    """The distributions an extra installs, read back from this package's own metadata."""
    requirements = metadata(_DISTRIBUTION_NAME).get_all("Requires-Dist") or []
    return frozenset(
        name.group(1)
        for requirement in requirements
        if (marker := _EXTRA_MARKER.search(requirement)) and marker.group(1) == extra
        if (name := _REQUIREMENT_NAME.match(requirement))
    )


@cache
def _is_installed(distribution_name: str) -> bool:
    """Whether a distribution is present in the running environment."""
    try:
        distribution(distribution_name)
    except PackageNotFoundError:
        return False
    return True
