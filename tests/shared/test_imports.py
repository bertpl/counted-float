"""The public export surface of each importable module: everything ours is advertised, and resolves."""

import importlib
import json
import subprocess
import sys
import textwrap

import pytest

PACKAGE = "counted_float"
PUBLIC_MODULE_NAMES = [PACKAGE, f"{PACKAGE}.config", f"{PACKAGE}.benchmarking"]

# Discovers the public names a module binds from our own package. Runs in a fresh interpreter on
# purpose: importing any submodule anywhere in a process injects it as an attribute of its parent,
# so in a shared process this would report submodules the module never imported itself.
_DISCOVER_PUBLIC_NAMES = textwrap.dedent(
    """
    import importlib, json, sys

    def defining_module(obj):
        # where a class/function was defined, or a module's own name
        return getattr(obj, "__module__", None) or getattr(obj, "__name__", "") or ""

    module = importlib.import_module(sys.argv[1])
    print(json.dumps({
        "bound": sorted(
            name for name, obj in vars(module).items()
            if not name.startswith("_") and defining_module(obj).startswith("counted_float")
        ),
        "advertised": sorted(module.__all__),
    }))
    """
)


@pytest.mark.parametrize("module_name", PUBLIC_MODULE_NAMES)
def test_every_name_in_all_resolves(module_name: str):
    # --- arrange -----------------------------------------
    module = importlib.import_module(module_name)

    # --- act / assert ------------------------------------
    for name in module.__all__:
        assert getattr(module, name, None) is not None, f"{module_name}.__all__ advertises unresolvable '{name}'"


@pytest.mark.parametrize("module_name", PUBLIC_MODULE_NAMES)
def test_every_public_name_from_this_package_is_advertised(module_name: str):
    """Anything public a module imports from our own package must appear in its __all__.

    The counterpart of the test above: that one catches an __all__ entry that no longer resolves,
    this one catches a name that resolves but was never advertised. Importing such a name works
    either way, so only star imports and re-export-strict type checkers would ever notice.

    Names imported from outside the package (stdlib, third-party) are excluded -- re-exporting
    those is not this package's business.
    """
    # --- arrange -----------------------------------------
    result = subprocess.run(  # noqa: S603 -- fixed args, no user input
        [sys.executable, "-c", _DISCOVER_PUBLIC_NAMES, module_name],
        capture_output=True,
        text=True,
        check=True,
    )
    surface = json.loads(result.stdout)

    # --- act ---------------------------------------------
    unadvertised = set(surface["bound"]) - set(surface["advertised"])

    # --- assert ------------------------------------------
    assert not unadvertised, f"{module_name} exposes {sorted(unadvertised)} but does not list them in __all__"


def test_bare_import_stays_free_of_the_benchmarking_stack():
    """A bare `import counted_float` must not load the benchmarking subpackage or its heavy deps.

    The counting core never touches numba or llvmlite; only the benchmarking subpackage does, and
    it is reachable by importing it directly. Runs in a fresh interpreter on purpose: in a shared
    process, other tests' imports would already have populated sys.modules.
    """
    # --- arrange -----------------------------------------
    discover_loaded = textwrap.dedent(
        """
        import json, sys
        import counted_float
        watched = ("counted_float.benchmarking", "numba", "llvmlite")
        print(json.dumps([name for name in watched if name in sys.modules]))
        """
    )

    # --- act ---------------------------------------------
    result = subprocess.run(  # noqa: S603 -- fixed args, no user input
        [sys.executable, "-c", discover_loaded],
        capture_output=True,
        text=True,
        check=True,
    )
    loaded = json.loads(result.stdout)

    # --- assert ------------------------------------------
    assert loaded == [], f"bare import loaded {loaded}"
