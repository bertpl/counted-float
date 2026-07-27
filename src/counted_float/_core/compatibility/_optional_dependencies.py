"""Optional capabilities, derived from the extras this package declares.

A **capability** is an extra. `pyproject.toml` is the single source of truth for what capabilities
exist and what each one needs, and this module reads that back from the installed distribution's own
metadata rather than restating any of it:

- `Provides-Extra` -> the set of capabilities
- the ``extra == '<name>'`` markers on `Requires-Dist` -> the distributions each capability needs

So adding a package to an extra needs no change here, and renaming an extra cannot leave a guard
telling users to install something that no longer resolves. Guard sites name a capability and
nothing else; `requires()` owns the only translation from a failed import into install guidance.

**What is checked is installation, not importability.** The metadata names *distributions*, and an
absent distribution cannot be mapped to the module names an import check would need — `py-cpuinfo`
provides `cpuinfo`, and nothing on the system knows that once the package is gone. A distribution
that is installed but broken therefore reads as present. Someone who acquires a package by a route
other than our extra is unaffected: it is installed either way, which is the case that matters.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from importlib.metadata import PackageNotFoundError, distribution, metadata

_DISTRIBUTION_NAME = "counted-float"

# The capabilities this codebase guards, so that a guard site names one of these rather than spelling
# an extra out inline. These are the only packaging facts stated here: which extra covers which part
# of the code, which is a statement no metadata can make for us. Every one is checked against the
# declared extras before use, so a rename in pyproject.toml fails loudly instead of guarding nothing.
CAP_CLI = "cli"
CAP_FLOPS_BENCHMARKING = "numba"

# `numpy>=2.1; (python_version == '3.13') and extra == 'benchmarking'` -> name `numpy`, extra
# `benchmarking`. Version specifiers and environment markers are deliberately dropped: this answers
# "is it here", and a leg-specific marker would make the answer depend on the interpreter.
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_EXTRA_MARKER = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")


# =================================================================================================
#  Reading the declared extras
# =================================================================================================
class MissingCapabilityError(ImportError):
    """A capability was reached without the extra that makes it work."""


class UnknownCapabilityError(LookupError):
    """A capability was named that this package does not declare as an extra."""


@cache
def capabilities() -> frozenset[str]:
    """Every capability this package declares, i.e. every extra it can be installed with."""
    return frozenset(metadata(_DISTRIBUTION_NAME).get_all("Provides-Extra") or ())


@cache
def required_distributions(capability: str) -> frozenset[str]:
    """The distributions a capability needs, as named by the extra that installs them."""
    _check_declared(capability)
    requirements = metadata(_DISTRIBUTION_NAME).get_all("Requires-Dist") or []
    return frozenset(
        name.group(1)
        for requirement in requirements
        if (marker := _EXTRA_MARKER.search(requirement)) and marker.group(1) == capability
        if (name := _REQUIREMENT_NAME.match(requirement))
    )


def _check_declared(capability: str) -> None:
    """Reject a capability this package does not declare, rather than silently guarding nothing."""
    if capability not in capabilities():
        declared = ", ".join(sorted(capabilities()))
        raise UnknownCapabilityError(f"{capability!r} is not a declared extra; this package has: {declared}")


# =================================================================================================
#  Asking whether a capability is usable
# =================================================================================================
@cache
def _is_installed(distribution_name: str) -> bool:
    """Whether a distribution is present in the running environment."""
    try:
        distribution(distribution_name)
    except PackageNotFoundError:
        return False
    return True


@cache
def is_available(capability: str) -> bool:
    """Whether every distribution this capability needs is installed."""
    return all(_is_installed(name) for name in required_distributions(capability))


def missing_message(capability: str) -> str:
    """The actionable install line shown when a capability is reached without its extra."""
    _check_declared(capability)
    return f'This feature requires the "{capability}" extra: pip install "{_DISTRIBUTION_NAME}[{capability}]"'


# =================================================================================================
#  Guarding a capability's entry point
# =================================================================================================
@contextmanager
def requires(capability: str) -> Iterator[None]:
    """Refuse to enter the block unless the capability is installed, naming what to install if not.

    A precondition rather than a translated failure: the block runs only once the extra is known to
    be present, so a genuine error inside it surfaces as itself instead of being relabelled as a
    packaging problem.
    """
    _check_declared(capability)
    if not is_available(capability):
        raise MissingCapabilityError(missing_message(capability))

    yield
