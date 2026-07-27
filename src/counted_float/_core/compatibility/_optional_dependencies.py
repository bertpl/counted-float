"""Optional capabilities: what they are, whether they are available, and what to say when they are not.

A capability is a slice of this package that only works when an extra was installed. Each one is
declared once below, and everything else — the runtime guards and the tests' skip conditions — goes
through that declaration.

Two things are deliberately *not* declared here:

- **Which third-party packages an extra installs.** That list lives in `pyproject.toml`, and
  restating it in code would be a second copy to keep in sync, in the one place where being wrong is
  silent. A capability instead names the module of *ours* that pulls those packages in, and asking
  whether the capability is available means asking whether that module imports. It stays correct
  when an extra gains or loses a package, because it never knew the packages to begin with.
- **Which failure counts as a missing dependency.** `requires()` owns the one try/except in the
  codebase; call sites state what they need and stay free of import bookkeeping.

The question a capability answers is importability, not packaging state. Someone who installs the
base package and acquires the modules by another route has a working capability, and there is no
reason to deny it because an extra was never named on the install line.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache


# =================================================================================================
#  Importability
# =================================================================================================
@cache
def is_importable(module_name: str) -> bool:
    """Whether a module can actually be imported, cached for the life of the process.

    Imports the module rather than looking for its spec: a distribution that is installed but
    unimportable — a broken wheel, an ABI mismatch against the running interpreter — is not a
    capability the caller can use, and reporting it as present would only move the failure later.
    """
    try:
        __import__(module_name)
    except ImportError:
        return False
    return True


# =================================================================================================
#  Capabilities
# =================================================================================================
class MissingCapabilityError(ImportError):
    """A capability was reached without the extra that makes it work."""


@dataclass(frozen=True)
class Capability:
    """A part of this package that an extra has to be installed for."""

    name: str
    """Human-facing name, as it appears at the front of the guard message."""

    extra: str
    """The extra that makes this capability work, as declared in the project metadata."""

    probe: str
    """The module of ours whose import needs that extra — the capability in one importable name."""

    def is_available(self) -> bool:
        """Whether this capability can be used in the running environment."""
        return is_importable(self.probe)

    def missing_message(self) -> str:
        """The actionable install line shown when the capability is reached without its extra."""
        return f'{self.name} requires the "{self.extra}" extra: pip install "counted-float[{self.extra}]"'


CAP_CLI = Capability(
    name="The counted_float CLI",
    extra="cli",
    probe="counted_float._core._cli",
)

CAP_FLOPS_BENCHMARKING = Capability(
    name="The flops benchmark suite",
    extra="numba",
    probe="counted_float._core.benchmarking.flops",
)


# =================================================================================================
#  Guarding a capability's entry point
# =================================================================================================
@contextmanager
def requires(capability: Capability) -> Iterator[None]:
    """Turn a failed import inside the block into this capability's install guidance.

    Wrap the import that reaches the capability, and nothing else — everything inside is code that
    only runs when the extra is present, so any import that fails there is that extra missing. The
    original error is chained rather than discarded, so the module that was actually absent stays
    one line down the traceback.
    """
    try:
        yield
    except ImportError as e:
        raise MissingCapabilityError(capability.missing_message()) from e
