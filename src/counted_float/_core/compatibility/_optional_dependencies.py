"""One place to ask whether an optional dependency is present, and one wording for saying it is not.

Two capabilities of this package sit behind optional dependencies, and each guard grew its own way
of asking: the numba shim kept a module-level flag, the CLI entry point matched a module name inline
against a hand-written install string, and the tests spelled out skip conditions of their own. They
all answer the same question, so they answer it here.

The question is importability, not packaging state. A user who installs the base package and
acquires the modules by some other route has a working capability, and there is no reason to deny it
because an extra was never named on the install line. That also keeps the predicates answerable
without reading installation metadata, which is what makes them usable as test skip conditions.
"""

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
    Importing here costs nothing extra, since every caller is about to import it anyway.
    """
    try:
        __import__(module_name)
    except ImportError:
        return False
    return True


# =================================================================================================
#  Capabilities behind an extra
# =================================================================================================
@dataclass(frozen=True)
class OptionalCapability:
    """A capability that only works when the optional modules it needs are importable."""

    name: str
    """Human-facing name of the capability, as it appears at the front of the guard message."""

    extra: str
    """The extra that installs this capability's modules."""

    modules: tuple[str, ...]
    """The modules the code imports for this capability — module names, not distribution names."""

    def is_importable(self) -> bool:
        """Whether every module this capability needs can be imported."""
        return all(is_importable(module_name) for module_name in self.modules)

    def explains(self, error: ModuleNotFoundError) -> bool:
        """Whether a failed import is this capability's missing dependency rather than an unrelated one."""
        return error.name in self.modules

    def missing_dependency_message(self) -> str:
        """The actionable install line shown when this capability is reached without its modules."""
        return f'{self.name} requires the "{self.extra}" extra: pip install "counted-float[{self.extra}]"'


CLI = OptionalCapability(
    name="The counted_float CLI",
    extra="cli",
    modules=("click",),
)

FLOPS_BENCHMARKING = OptionalCapability(
    name="The flops benchmark suite",
    extra="numba",
    # Deliberately without numba, even though the same extra installs it: numba is shimmed, so its
    # absence costs accuracy rather than availability -- the suite still imports and still runs, and
    # the shim's own code paths are exercised precisely by running these tests without it. Listing
    # it here would make the capability read as unavailable whenever numba is missing, which silently
    # takes the shim's test coverage with it. Its absence is asked about via is_numba_importable().
    #
    # These three are still base dependencies, so none of them can be missing today. They are named
    # because this is what the capability reaches, independently of which tier currently ships them.
    modules=("numpy", "psutil", "cpuinfo"),
)
